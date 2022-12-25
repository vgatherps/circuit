#include "replay/collator.hh"

#include <algorithm>
#include <cstdint>
#include <deque>

#include "gtest/gtest.h"

using IPair = std::tuple<std::uint64_t, std::uint64_t>;

template <> std::uint64_t get_local_timestamp<IPair>(const IPair &p) {
  return std::get<0>(p);
}

class OrderedTsTags final : public CollatorSource<IPair> {
  std::deque<IPair> timestamps;

public:
  std::optional<IPair> next_element() override {

    if (timestamps.size() == 0) {
      return {};
    }

    IPair ts = timestamps.front();
    timestamps.pop_front();

    return ts;
  }

  OrderedTsTags(std::vector<IPair> in_ts, bool sort = true) {
    if (sort) {
      std::sort(in_ts.begin(), in_ts.end());
    }

    timestamps.insert(timestamps.end(), in_ts.begin(), in_ts.end());
  }

  OrderedTsTags() = default;
  OrderedTsTags(const OrderedTsTags &) = default;
};

TEST(CollatorTest, SingleOrderedCollator) {

  OrderedTsTags tags({{1, 2}, {2, 3}});
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}

TEST(CollatorTest, SingleUnorderedCollator) {

  OrderedTsTags tags({{2, 3}, {1, 2}}, false);
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}

TEST(CollatorTest, MultiOrderedCollators) {

  OrderedTsTags tags({{1, 2}, {2, 3}});
  OrderedTsTags tags_2({{0, 2}, {4, 3}});
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);
  std::unique_ptr<CollatorSource<IPair>> tags_2_p =
      std::make_unique<OrderedTsTags>(tags_2);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));
  v.emplace_back(std::move(tags_2_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(0, 2));
  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), IPair(4, 3));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}

TEST(CollatorTest, MultiUnOrderedCollators) {

  OrderedTsTags tags({{1, 2}, {2, 3}});
  OrderedTsTags tags_2({{4, 2}, {0, 3}}, false);
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);
  std::unique_ptr<CollatorSource<IPair>> tags_2_p =
      std::make_unique<OrderedTsTags>(tags_2);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));
  v.emplace_back(std::move(tags_2_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), IPair(4, 2));
  EXPECT_EQ(collator.next_element(), IPair(0, 3));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}

TEST(CollatorTest, VaryLengthOrderedCollators) {

  OrderedTsTags tags({{1, 2}, {2, 3}, {5, 6}});
  OrderedTsTags tags_2({{0, 2}, {4, 3}});
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);
  std::unique_ptr<CollatorSource<IPair>> tags_2_p =
      std::make_unique<OrderedTsTags>(tags_2);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));
  v.emplace_back(std::move(tags_2_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(0, 2));
  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), IPair(4, 3));
  EXPECT_EQ(collator.next_element(), IPair(5, 6));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}

TEST(CollatorTest, VaryLengthUnOrderedCollators) {

  OrderedTsTags tags({{1, 2}, {2, 3}});
  OrderedTsTags tags_2({{0, 1}, {4, 2}, {0, 3}}, false);
  std::unique_ptr<CollatorSource<IPair>> tags_p =
      std::make_unique<OrderedTsTags>(tags);
  std::unique_ptr<CollatorSource<IPair>> tags_2_p =
      std::make_unique<OrderedTsTags>(tags_2);

  std::vector<std::unique_ptr<CollatorSource<IPair>>> v;
  v.emplace_back(std::move(tags_p));
  v.emplace_back(std::move(tags_2_p));

  Collator<IPair> collator(std::move(v));

  EXPECT_EQ(collator.next_element(), IPair(0, 1));
  EXPECT_EQ(collator.next_element(), IPair(1, 2));
  EXPECT_EQ(collator.next_element(), IPair(2, 3));
  EXPECT_EQ(collator.next_element(), IPair(4, 2));
  EXPECT_EQ(collator.next_element(), IPair(0, 3));
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
  EXPECT_EQ(collator.next_element(), std::optional<IPair>());
}