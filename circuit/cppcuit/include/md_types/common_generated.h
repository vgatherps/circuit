// automatically generated by the FlatBuffers compiler, do not modify


#ifndef FLATBUFFERS_GENERATED_COMMON_H_
#define FLATBUFFERS_GENERATED_COMMON_H_

#include "flatbuffers/flatbuffers.h"

// Ensure the included flatbuffers.h is the same version as when this file was
// generated, otherwise it may not be compatible.
static_assert(FLATBUFFERS_VERSION_MAJOR == 22 &&
              FLATBUFFERS_VERSION_MINOR == 12 &&
              FLATBUFFERS_VERSION_REVISION == 6,
             "Non-compatible flatbuffers version included");

struct Level;

struct Trade;

struct DepthUpdate;
struct DepthUpdateBuilder;

struct TradeUpdate;
struct TradeUpdateBuilder;

struct BboUpdate;
struct BboUpdateBuilder;

enum RawMdMessage : uint8_t {
  RawMdMessage_NONE = 0,
  RawMdMessage_trades = 1,
  RawMdMessage_bbo = 2,
  RawMdMessage_depth = 3,
  RawMdMessage_MIN = RawMdMessage_NONE,
  RawMdMessage_MAX = RawMdMessage_depth
};

inline const RawMdMessage (&EnumValuesRawMdMessage())[4] {
  static const RawMdMessage values[] = {
    RawMdMessage_NONE,
    RawMdMessage_trades,
    RawMdMessage_bbo,
    RawMdMessage_depth
  };
  return values;
}

inline const char * const *EnumNamesRawMdMessage() {
  static const char * const names[5] = {
    "NONE",
    "trades",
    "bbo",
    "depth",
    nullptr
  };
  return names;
}

inline const char *EnumNameRawMdMessage(RawMdMessage e) {
  if (flatbuffers::IsOutRange(e, RawMdMessage_NONE, RawMdMessage_depth)) return "";
  const size_t index = static_cast<size_t>(e);
  return EnumNamesRawMdMessage()[index];
}

template<typename T> struct RawMdMessageTraits {
  static const RawMdMessage enum_value = RawMdMessage_NONE;
};

template<> struct RawMdMessageTraits<TradeUpdate> {
  static const RawMdMessage enum_value = RawMdMessage_trades;
};

template<> struct RawMdMessageTraits<BboUpdate> {
  static const RawMdMessage enum_value = RawMdMessage_bbo;
};

template<> struct RawMdMessageTraits<DepthUpdate> {
  static const RawMdMessage enum_value = RawMdMessage_depth;
};

bool VerifyRawMdMessage(flatbuffers::Verifier &verifier, const void *obj, RawMdMessage type);
bool VerifyRawMdMessageVector(flatbuffers::Verifier &verifier, const flatbuffers::Vector<flatbuffers::Offset<void>> *values, const flatbuffers::Vector<uint8_t> *types);

FLATBUFFERS_MANUALLY_ALIGNED_STRUCT(8) Level FLATBUFFERS_FINAL_CLASS {
 private:
  double price_;
  double size_;

 public:
  Level()
      : price_(0),
        size_(0) {
  }
  Level(double _price, double _size)
      : price_(flatbuffers::EndianScalar(_price)),
        size_(flatbuffers::EndianScalar(_size)) {
  }
  double price() const {
    return flatbuffers::EndianScalar(price_);
  }
  double size() const {
    return flatbuffers::EndianScalar(size_);
  }
};
FLATBUFFERS_STRUCT_END(Level, 16);

FLATBUFFERS_MANUALLY_ALIGNED_STRUCT(8) Trade FLATBUFFERS_FINAL_CLASS {
 private:
  double price_;
  double size_;
  int64_t exchange_time_us_;
  uint8_t buy_;
  int8_t padding0__;  int16_t padding1__;  int32_t padding2__;

 public:
  Trade()
      : price_(0),
        size_(0),
        exchange_time_us_(0),
        buy_(0),
        padding0__(0),
        padding1__(0),
        padding2__(0) {
    (void)padding0__;
    (void)padding1__;
    (void)padding2__;
  }
  Trade(double _price, double _size, int64_t _exchange_time_us, bool _buy)
      : price_(flatbuffers::EndianScalar(_price)),
        size_(flatbuffers::EndianScalar(_size)),
        exchange_time_us_(flatbuffers::EndianScalar(_exchange_time_us)),
        buy_(flatbuffers::EndianScalar(static_cast<uint8_t>(_buy))),
        padding0__(0),
        padding1__(0),
        padding2__(0) {
    (void)padding0__;
    (void)padding1__;
    (void)padding2__;
  }
  double price() const {
    return flatbuffers::EndianScalar(price_);
  }
  double size() const {
    return flatbuffers::EndianScalar(size_);
  }
  int64_t exchange_time_us() const {
    return flatbuffers::EndianScalar(exchange_time_us_);
  }
  bool buy() const {
    return flatbuffers::EndianScalar(buy_) != 0;
  }
};
FLATBUFFERS_STRUCT_END(Trade, 32);

struct DepthUpdate FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef DepthUpdateBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_BIDS = 4,
    VT_ASKS = 6,
    VT_EXCHANGE_TIME_US = 8
  };
  const flatbuffers::Vector<const Level *> *bids() const {
    return GetPointer<const flatbuffers::Vector<const Level *> *>(VT_BIDS);
  }
  const flatbuffers::Vector<const Level *> *asks() const {
    return GetPointer<const flatbuffers::Vector<const Level *> *>(VT_ASKS);
  }
  int64_t exchange_time_us() const {
    return GetField<int64_t>(VT_EXCHANGE_TIME_US, 0);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyOffset(verifier, VT_BIDS) &&
           verifier.VerifyVector(bids()) &&
           VerifyOffset(verifier, VT_ASKS) &&
           verifier.VerifyVector(asks()) &&
           VerifyField<int64_t>(verifier, VT_EXCHANGE_TIME_US, 8) &&
           verifier.EndTable();
  }
};

struct DepthUpdateBuilder {
  typedef DepthUpdate Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_bids(flatbuffers::Offset<flatbuffers::Vector<const Level *>> bids) {
    fbb_.AddOffset(DepthUpdate::VT_BIDS, bids);
  }
  void add_asks(flatbuffers::Offset<flatbuffers::Vector<const Level *>> asks) {
    fbb_.AddOffset(DepthUpdate::VT_ASKS, asks);
  }
  void add_exchange_time_us(int64_t exchange_time_us) {
    fbb_.AddElement<int64_t>(DepthUpdate::VT_EXCHANGE_TIME_US, exchange_time_us, 0);
  }
  explicit DepthUpdateBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<DepthUpdate> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<DepthUpdate>(end);
    return o;
  }
};

inline flatbuffers::Offset<DepthUpdate> CreateDepthUpdate(
    flatbuffers::FlatBufferBuilder &_fbb,
    flatbuffers::Offset<flatbuffers::Vector<const Level *>> bids = 0,
    flatbuffers::Offset<flatbuffers::Vector<const Level *>> asks = 0,
    int64_t exchange_time_us = 0) {
  DepthUpdateBuilder builder_(_fbb);
  builder_.add_exchange_time_us(exchange_time_us);
  builder_.add_asks(asks);
  builder_.add_bids(bids);
  return builder_.Finish();
}

inline flatbuffers::Offset<DepthUpdate> CreateDepthUpdateDirect(
    flatbuffers::FlatBufferBuilder &_fbb,
    const std::vector<Level> *bids = nullptr,
    const std::vector<Level> *asks = nullptr,
    int64_t exchange_time_us = 0) {
  auto bids__ = bids ? _fbb.CreateVectorOfStructs<Level>(*bids) : 0;
  auto asks__ = asks ? _fbb.CreateVectorOfStructs<Level>(*asks) : 0;
  return CreateDepthUpdate(
      _fbb,
      bids__,
      asks__,
      exchange_time_us);
}

struct TradeUpdate FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef TradeUpdateBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_TRADES = 4
  };
  const flatbuffers::Vector<const Trade *> *trades() const {
    return GetPointer<const flatbuffers::Vector<const Trade *> *>(VT_TRADES);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyOffset(verifier, VT_TRADES) &&
           verifier.VerifyVector(trades()) &&
           verifier.EndTable();
  }
};

struct TradeUpdateBuilder {
  typedef TradeUpdate Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_trades(flatbuffers::Offset<flatbuffers::Vector<const Trade *>> trades) {
    fbb_.AddOffset(TradeUpdate::VT_TRADES, trades);
  }
  explicit TradeUpdateBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<TradeUpdate> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<TradeUpdate>(end);
    return o;
  }
};

inline flatbuffers::Offset<TradeUpdate> CreateTradeUpdate(
    flatbuffers::FlatBufferBuilder &_fbb,
    flatbuffers::Offset<flatbuffers::Vector<const Trade *>> trades = 0) {
  TradeUpdateBuilder builder_(_fbb);
  builder_.add_trades(trades);
  return builder_.Finish();
}

inline flatbuffers::Offset<TradeUpdate> CreateTradeUpdateDirect(
    flatbuffers::FlatBufferBuilder &_fbb,
    const std::vector<Trade> *trades = nullptr) {
  auto trades__ = trades ? _fbb.CreateVectorOfStructs<Trade>(*trades) : 0;
  return CreateTradeUpdate(
      _fbb,
      trades__);
}

struct BboUpdate FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef BboUpdateBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_BID = 4,
    VT_ASK = 6,
    VT_EXCHANGE_TIME_US = 8
  };
  const Level *bid() const {
    return GetStruct<const Level *>(VT_BID);
  }
  const Level *ask() const {
    return GetStruct<const Level *>(VT_ASK);
  }
  int64_t exchange_time_us() const {
    return GetField<int64_t>(VT_EXCHANGE_TIME_US, 0);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyField<Level>(verifier, VT_BID, 8) &&
           VerifyField<Level>(verifier, VT_ASK, 8) &&
           VerifyField<int64_t>(verifier, VT_EXCHANGE_TIME_US, 8) &&
           verifier.EndTable();
  }
};

struct BboUpdateBuilder {
  typedef BboUpdate Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_bid(const Level *bid) {
    fbb_.AddStruct(BboUpdate::VT_BID, bid);
  }
  void add_ask(const Level *ask) {
    fbb_.AddStruct(BboUpdate::VT_ASK, ask);
  }
  void add_exchange_time_us(int64_t exchange_time_us) {
    fbb_.AddElement<int64_t>(BboUpdate::VT_EXCHANGE_TIME_US, exchange_time_us, 0);
  }
  explicit BboUpdateBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<BboUpdate> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<BboUpdate>(end);
    return o;
  }
};

inline flatbuffers::Offset<BboUpdate> CreateBboUpdate(
    flatbuffers::FlatBufferBuilder &_fbb,
    const Level *bid = nullptr,
    const Level *ask = nullptr,
    int64_t exchange_time_us = 0) {
  BboUpdateBuilder builder_(_fbb);
  builder_.add_exchange_time_us(exchange_time_us);
  builder_.add_ask(ask);
  builder_.add_bid(bid);
  return builder_.Finish();
}

inline bool VerifyRawMdMessage(flatbuffers::Verifier &verifier, const void *obj, RawMdMessage type) {
  switch (type) {
    case RawMdMessage_NONE: {
      return true;
    }
    case RawMdMessage_trades: {
      auto ptr = reinterpret_cast<const TradeUpdate *>(obj);
      return verifier.VerifyTable(ptr);
    }
    case RawMdMessage_bbo: {
      auto ptr = reinterpret_cast<const BboUpdate *>(obj);
      return verifier.VerifyTable(ptr);
    }
    case RawMdMessage_depth: {
      auto ptr = reinterpret_cast<const DepthUpdate *>(obj);
      return verifier.VerifyTable(ptr);
    }
    default: return true;
  }
}

inline bool VerifyRawMdMessageVector(flatbuffers::Verifier &verifier, const flatbuffers::Vector<flatbuffers::Offset<void>> *values, const flatbuffers::Vector<uint8_t> *types) {
  if (!values || !types) return !values && !types;
  if (values->size() != types->size()) return false;
  for (flatbuffers::uoffset_t i = 0; i < values->size(); ++i) {
    if (!VerifyRawMdMessage(
        verifier,  values->Get(i), types->GetEnum<RawMdMessage>(i))) {
      return false;
    }
  }
  return true;
}

#endif  // FLATBUFFERS_GENERATED_COMMON_H_
