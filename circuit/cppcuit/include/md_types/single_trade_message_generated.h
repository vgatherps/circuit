// automatically generated by the FlatBuffers compiler, do not modify


#ifndef FLATBUFFERS_GENERATED_SINGLETRADEMESSAGE_H_
#define FLATBUFFERS_GENERATED_SINGLETRADEMESSAGE_H_

#include "flatbuffers/flatbuffers.h"

// Ensure the included flatbuffers.h is the same version as when this file was
// generated, otherwise it may not be compatible.
static_assert(FLATBUFFERS_VERSION_MAJOR == 22 &&
              FLATBUFFERS_VERSION_MINOR == 12 &&
              FLATBUFFERS_VERSION_REVISION == 6,
             "Non-compatible flatbuffers version included");

#include "common_generated.h"

struct SingleTradeMessage;
struct SingleTradeMessageBuilder;

struct SingleTradeMessage FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef SingleTradeMessageBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_LOCAL_TIME_US = 4,
    VT_MESSAGE = 6
  };
  int64_t local_time_us() const {
    return GetField<int64_t>(VT_LOCAL_TIME_US, 0);
  }
  const Trade *message() const {
    return GetStruct<const Trade *>(VT_MESSAGE);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyField<int64_t>(verifier, VT_LOCAL_TIME_US, 8) &&
           VerifyField<Trade>(verifier, VT_MESSAGE, 8) &&
           verifier.EndTable();
  }
};

struct SingleTradeMessageBuilder {
  typedef SingleTradeMessage Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_local_time_us(int64_t local_time_us) {
    fbb_.AddElement<int64_t>(SingleTradeMessage::VT_LOCAL_TIME_US, local_time_us, 0);
  }
  void add_message(const Trade *message) {
    fbb_.AddStruct(SingleTradeMessage::VT_MESSAGE, message);
  }
  explicit SingleTradeMessageBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<SingleTradeMessage> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<SingleTradeMessage>(end);
    return o;
  }
};

inline flatbuffers::Offset<SingleTradeMessage> CreateSingleTradeMessage(
    flatbuffers::FlatBufferBuilder &_fbb,
    int64_t local_time_us = 0,
    const Trade *message = nullptr) {
  SingleTradeMessageBuilder builder_(_fbb);
  builder_.add_local_time_us(local_time_us);
  builder_.add_message(message);
  return builder_.Finish();
}

inline const SingleTradeMessage *GetSingleTradeMessage(const void *buf) {
  return flatbuffers::GetRoot<SingleTradeMessage>(buf);
}

inline const SingleTradeMessage *GetSizePrefixedSingleTradeMessage(const void *buf) {
  return flatbuffers::GetSizePrefixedRoot<SingleTradeMessage>(buf);
}

inline bool VerifySingleTradeMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifyBuffer<SingleTradeMessage>(nullptr);
}

inline bool VerifySizePrefixedSingleTradeMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifySizePrefixedBuffer<SingleTradeMessage>(nullptr);
}

inline void FinishSingleTradeMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<SingleTradeMessage> root) {
  fbb.Finish(root);
}

inline void FinishSizePrefixedSingleTradeMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<SingleTradeMessage> root) {
  fbb.FinishSizePrefixed(root);
}

#endif  // FLATBUFFERS_GENERATED_SINGLETRADEMESSAGE_H_
