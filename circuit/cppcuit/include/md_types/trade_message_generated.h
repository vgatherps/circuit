// automatically generated by the FlatBuffers compiler, do not modify


#ifndef FLATBUFFERS_GENERATED_TRADEMESSAGE_H_
#define FLATBUFFERS_GENERATED_TRADEMESSAGE_H_

#include "flatbuffers/flatbuffers.h"

// Ensure the included flatbuffers.h is the same version as when this file was
// generated, otherwise it may not be compatible.
static_assert(FLATBUFFERS_VERSION_MAJOR == 22 &&
              FLATBUFFERS_VERSION_MINOR == 12 &&
              FLATBUFFERS_VERSION_REVISION == 6,
             "Non-compatible flatbuffers version included");

#include "common_generated.h"

struct TradeMessage;
struct TradeMessageBuilder;

struct TradeMessage FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef TradeMessageBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_LOCAL_TIME_US = 4,
    VT_MESSAGE = 6
  };
  int64_t local_time_us() const {
    return GetField<int64_t>(VT_LOCAL_TIME_US, 0);
  }
  const TradeUpdate *message() const {
    return GetPointer<const TradeUpdate *>(VT_MESSAGE);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyField<int64_t>(verifier, VT_LOCAL_TIME_US, 8) &&
           VerifyOffset(verifier, VT_MESSAGE) &&
           verifier.VerifyTable(message()) &&
           verifier.EndTable();
  }
};

struct TradeMessageBuilder {
  typedef TradeMessage Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_local_time_us(int64_t local_time_us) {
    fbb_.AddElement<int64_t>(TradeMessage::VT_LOCAL_TIME_US, local_time_us, 0);
  }
  void add_message(flatbuffers::Offset<TradeUpdate> message) {
    fbb_.AddOffset(TradeMessage::VT_MESSAGE, message);
  }
  explicit TradeMessageBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<TradeMessage> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<TradeMessage>(end);
    return o;
  }
};

inline flatbuffers::Offset<TradeMessage> CreateTradeMessage(
    flatbuffers::FlatBufferBuilder &_fbb,
    int64_t local_time_us = 0,
    flatbuffers::Offset<TradeUpdate> message = 0) {
  TradeMessageBuilder builder_(_fbb);
  builder_.add_local_time_us(local_time_us);
  builder_.add_message(message);
  return builder_.Finish();
}

inline const TradeMessage *GetTradeMessage(const void *buf) {
  return flatbuffers::GetRoot<TradeMessage>(buf);
}

inline const TradeMessage *GetSizePrefixedTradeMessage(const void *buf) {
  return flatbuffers::GetSizePrefixedRoot<TradeMessage>(buf);
}

inline bool VerifyTradeMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifyBuffer<TradeMessage>(nullptr);
}

inline bool VerifySizePrefixedTradeMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifySizePrefixedBuffer<TradeMessage>(nullptr);
}

inline void FinishTradeMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<TradeMessage> root) {
  fbb.Finish(root);
}

inline void FinishSizePrefixedTradeMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<TradeMessage> root) {
  fbb.FinishSizePrefixed(root);
}

#endif  // FLATBUFFERS_GENERATED_TRADEMESSAGE_H_
