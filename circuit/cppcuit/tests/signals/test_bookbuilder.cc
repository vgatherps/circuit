#include "signals/book_pressure/book_updater.hh"
#include "signals/bookbuilder.hh"

#include "md_types/depth_message_generated.h"

#include <include/gtest/gtest.h>

#include <vector>

flatbuffers::FlatBufferBuilder
create_depth_update(std::vector<std::tuple<double, double>> bids,
                    std::vector<std::tuple<double, double>> asks) {
  flatbuffers::FlatBufferBuilder builder;
  std::vector<Level> f_bids, f_asks;

  for (auto [bid_price, bid_size] : bids) {
    f_bids.push_back(Level(bid_price, bid_size));
  }
  for (auto [ask_price, ask_size] : asks) {
    f_asks.push_back(Level(ask_price, ask_size));
  }

  auto fb_bids = builder.CreateVectorOfStructs(f_bids);
  auto fb_asks = builder.CreateVectorOfStructs(f_asks);

  auto update_offset = CreateDepthUpdate(builder, fb_bids, fb_asks, 0);

  auto offset = CreateDepthMessage(builder, 0, update_offset);

  builder.Finish(offset);

  return std::move(builder);
}

const DepthUpdate *get_update(const flatbuffers::FlatBufferBuilder &buf) {

  flatbuffers::Verifier ver((const std::uint8_t *)buf.GetBufferPointer(),
                            buf.GetSize());
  EXPECT_TRUE(VerifyDepthMessageBuffer(ver));
  return GetDepthMessage(buf.GetBufferPointer())->message();
}

void check_book_levels(const BookBuilder<double, double> &book,
                       std::vector<std::tuple<double, double>> bids,
                       std::vector<std::tuple<double, double>> asks) {
  int bid_idx = 0;
  for (auto [price, size] : book.bid_levels()) {
    ASSERT_GT(bids.size(), 0) << "Book bids had more fields than examples";
    auto [expected_price, expected_size] = bids[0];
    EXPECT_DOUBLE_EQ(price, expected_price)
        << "Got wrong price on bid #" << bid_idx;
    EXPECT_DOUBLE_EQ(size, expected_size)
        << "Got wrong price on bid #" << bid_idx;
    bids.erase(bids.begin());
    bid_idx += 1;
  }

  EXPECT_EQ(bids.size(), 0) << "Book bids were empty before examples";

  int ask_idx = 0;
  for (auto [price, size] : book.ask_levels()) {
    ASSERT_GT(asks.size(), 0) << "Book asks had more fields than examples";
    auto [expected_price, expected_size] = asks[0];
    EXPECT_DOUBLE_EQ(price, expected_price)
        << "Got wrong price on ask #" << ask_idx;
    EXPECT_DOUBLE_EQ(size, expected_size)
        << "Got wrong price on ask #" << ask_idx;
    asks.erase(asks.begin());
    ask_idx += 1;
  }

  EXPECT_EQ(asks.size(), 0) << "Book asks were empty before examples";
}

void check_updates(std::vector<AnnotatedLevel> side,
                   std::vector<AnnotatedLevel> expected,
                   const char *side_name) {
  ASSERT_EQ(side.size(), expected.size())
      << "Had " << side.size() << " updates on " << side_name << ", expected "
      << expected.size();

  for (int i = 0; i < expected.size(); i++) {
    EXPECT_DOUBLE_EQ(side[i].current_size, expected[i].current_size)
        << "Wrong current size on update idx " << i << " on side " << side_name;
    EXPECT_DOUBLE_EQ(side[i].previous_size, expected[i].previous_size)
        << "Wrong previous size on update idx " << i << " on side "
        << side_name;
    EXPECT_DOUBLE_EQ(side[i].price, expected[i].price)
        << "Wrong price on update idx " << i << " on side " << side_name;
  }
}

struct BookBuilderTestIter {
  std::vector<std::tuple<double, double>> bids, asks;
  std::vector<std::tuple<double, double>> expected_bids, expected_asks;

  std::optional<BBO> bbo;

  std::vector<AnnotatedLevel> bid_updates, ask_updates;
};

void run_test_loop(BookBuilder<double, double> &book,
                   BookBuilderTestIter test) {
  flatbuffers::FlatBufferBuilder builder =
      create_depth_update(test.bids, test.asks);

  const DepthUpdate *depth = get_update(builder);
  UpdatedLevels updates;
  BBO bbo;

  struct Outs {
    PlainBook &book;
    UpdatedLevels &updates;
    BBO &bbo;
  };

  struct Ins {
    optional_reference<const BookUpdater::ConstDepthUpdate> depth;
  };

  BookUpdater::OutputsValid validity = BookUpdater::on_depth(
      Ins{.depth = depth}, Outs{.book = book, .updates = updates, .bbo = bbo});

  EXPECT_TRUE(validity.updates) << "Updates validity alqways returns true";
  if (test.bbo.has_value()) {
    // TODO check for bbo equality
    EXPECT_DOUBLE_EQ(test.bbo->bid.price, bbo.bid.price);
    EXPECT_DOUBLE_EQ(test.bbo->bid.size, bbo.bid.size);
    EXPECT_DOUBLE_EQ(test.bbo->ask.price, bbo.ask.price);
    EXPECT_DOUBLE_EQ(test.bbo->ask.size, bbo.ask.size);
  } else {
    EXPECT_FALSE(validity.bbo) << "Got a valid bbo when it should be invalid";
  }

  check_book_levels(book, test.expected_bids, test.expected_asks);
  check_updates(updates.bids, test.bid_updates, "bid");
  check_updates(updates.asks, test.ask_updates, "ask");
}

TEST(BookBuilder, TestEmptyBook) {
  PlainBook book;
  BookBuilderTestIter empty;

  run_test_loop(book, empty);
}

TEST(BookBuilder, TestJustOneBid) {
  PlainBook book;
  BookBuilderTestIter just_bid{
      .bids = {{1.0, 10.0}},
      .expected_bids = {{1.0, 10.0}},
      .bid_updates = {
          {.price = 1.0, .previous_size = 0.0, .current_size = 10.0}}};

  run_test_loop(book, just_bid);
}

TEST(BookBuilder, TestJustOneAsk) {
  PlainBook book;
  BookBuilderTestIter just_ask{
      .asks = {{1.0, 10.0}},
      .expected_asks = {{1.0, 10.0}},
      .ask_updates = {
          {.price = 1.0, .previous_size = 0.0, .current_size = 10.0}}};

  run_test_loop(book, just_ask);
}

TEST(BookBuilder, TestBidAsk) {
  PlainBook book;
  BookBuilderTestIter bid_ask{

      .bids = {{0.5, 5.9}},
      .asks = {{1.0, 10.0}},
      .expected_bids = {{0.5, 5.9}},
      .expected_asks = {{1.0, 10.0}},
      .bbo = BBO{.bid = {.price = 0.5, .size = 5.9},
                 .ask = {.price = 1.0, .size = 10.0}},
      .bid_updates = {{.price = 0.5,
                       .previous_size = 0.0,
                       .current_size = 5.9}},
      .ask_updates = {
          {.price = 1.0, .previous_size = 0.0, .current_size = 10.0}}};

  run_test_loop(book, bid_ask);
}
static BookBuilderTestIter two_level_test{
    .bids = {{0.5, 5.9}, {0.3, 3.4}},
    .asks = {{1.0, 10.0}, {0.9, 11.1}},
    .expected_bids = {{0.5, 5.9}, {0.3, 3.4}},
    .expected_asks = {{0.9, 11.1}, {1.0, 10.0}},
    .bbo = BBO{.bid = {.price = 0.5, .size = 5.9},
               .ask = {.price = 0.9, .size = 11.1}},
    .bid_updates = {{.price = 0.5, .previous_size = 0.0, .current_size = 5.9},
                    {.price = 0.3, .previous_size = 0.0, .current_size = 3.4}},
    .ask_updates = {
        {.price = 1.0, .previous_size = 0.0, .current_size = 10.0},
        {.price = 0.9, .previous_size = 0.0, .current_size = 11.1}}};

TEST(BookBuilder, TestMultiBidAsk) {
  PlainBook book;

  run_test_loop(book, two_level_test);
}

TEST(BookBuilder, TestReplaceBid) {
  PlainBook book;
  BookBuilderTestIter replace_bid{
      .bids = {{0.5, 6.1}},
      .expected_bids = {{0.5, 6.1}, {0.3, 3.4}},
      .expected_asks = {{0.9, 11.1}, {1.0, 10.0}},
      .bbo = BBO{.bid = {.price = 0.5, .size = 6.1},
                 .ask = {.price = 0.9, .size = 11.1}},
      .bid_updates = {
          {.price = 0.5, .previous_size = 5.9, .current_size = 6.1}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, replace_bid);
}

TEST(BookBuilder, TestReplaceAsk) {
  PlainBook book;
  BookBuilderTestIter replace_ask{
      .asks = {{0.9, 3.2}},
      .expected_bids = {{0.5, 5.9}, {0.3, 3.4}},
      .expected_asks = {{0.9, 3.2}, {1.0, 10.0}},
      .bbo = BBO{.bid = {.price = 0.5, .size = 5.9},
                 .ask = {.price = 0.9, .size = 3.2}},
      .ask_updates = {
          {.price = 0.9, .previous_size = 11.1, .current_size = 3.2}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, replace_ask);
}

TEST(BookBuilder, TestDeleteBid) {
  PlainBook book;
  BookBuilderTestIter delete_bid{
      .bids = {{0.5, 0.0}},
      .expected_bids = {{0.3, 3.4}},
      .expected_asks = {{0.9, 11.1}, {1.0, 10.0}},
      .bbo = BBO{.bid = {.price = 0.3, .size = 3.4},
                 .ask = {.price = 0.9, .size = 11.1}},
      .bid_updates = {
          {.price = 0.5, .previous_size = 5.9, .current_size = 0.0}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, delete_bid);
}

TEST(BookBuilder, TestDeleteAsk) {
  PlainBook book;
  BookBuilderTestIter delete_ask{
      .asks = {{0.9, 0.0}},
      .expected_bids = {{0.5, 5.9}, {0.3, 3.4}},
      .expected_asks = {{1.0, 10.0}},
      .bbo = BBO{.bid = {.price = 0.5, .size = 5.9},
                 .ask = {.price = 1.0, .size = 10.0}},
      .ask_updates = {
          {.price = 0.9, .previous_size = 11.1, .current_size = 0.0}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, delete_ask);
}

TEST(BookBuilder, TestInvalidateBids) {
  PlainBook book;
  BookBuilderTestIter delete_bids{
      .bids = {{0.5, 0.0}, {0.3, 0.0}},
      .expected_bids = {},
      .expected_asks = {{0.9, 11.1}, {1.0, 10.0}},
      .bid_updates = {
          {.price = 0.5, .previous_size = 5.9, .current_size = 0.0},
          {.price = 0.3, .previous_size = 3.4, .current_size = 0.0}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, delete_bids);
}

TEST(BookBuilder, TestInvalidateAsks) {
  PlainBook book;
  BookBuilderTestIter delete_asks{
      .asks = {{0.9, 0.0}, {1.0, 0.0}},
      .expected_bids = {{0.5, 5.9}, {0.3, 3.4}},
      .expected_asks = {},
      .ask_updates = {
          {.price = 0.9, .previous_size = 11.1, .current_size = 0.0},
          {.price = 1.0, .previous_size = 10.0, .current_size = 0.0}}};

  run_test_loop(book, two_level_test);
  run_test_loop(book, delete_asks);
}