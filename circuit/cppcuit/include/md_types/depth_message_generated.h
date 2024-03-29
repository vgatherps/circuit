// automatically generated by the FlatBuffers compiler, do not modify


#ifndef FLATBUFFERS_GENERATED_DEPTHMESSAGE_H_
#define FLATBUFFERS_GENERATED_DEPTHMESSAGE_H_

#include "flatbuffers/flatbuffers.h"

// Ensure the included flatbuffers.h is the same version as when this file was
// generated, otherwise it may not be compatible.
static_assert(FLATBUFFERS_VERSION_MAJOR == 22 &&
              FLATBUFFERS_VERSION_MINOR == 12 &&
              FLATBUFFERS_VERSION_REVISION == 6,
             "Non-compatible flatbuffers version included");

#include "common_generated.h"

struct DepthMessage;
struct DepthMessageBuilder;

struct DepthMessage FLATBUFFERS_FINAL_CLASS : private flatbuffers::Table {
  typedef DepthMessageBuilder Builder;
  enum FlatBuffersVTableOffset FLATBUFFERS_VTABLE_UNDERLYING_TYPE {
    VT_LOCAL_TIME_US = 4,
    VT_MESSAGE = 6
  };
  int64_t local_time_us() const {
    return GetField<int64_t>(VT_LOCAL_TIME_US, 0);
  }
  const DepthUpdate *message() const {
    return GetPointer<const DepthUpdate *>(VT_MESSAGE);
  }
  bool Verify(flatbuffers::Verifier &verifier) const {
    return VerifyTableStart(verifier) &&
           VerifyField<int64_t>(verifier, VT_LOCAL_TIME_US, 8) &&
           VerifyOffset(verifier, VT_MESSAGE) &&
           verifier.VerifyTable(message()) &&
           verifier.EndTable();
  }
};

struct DepthMessageBuilder {
  typedef DepthMessage Table;
  flatbuffers::FlatBufferBuilder &fbb_;
  flatbuffers::uoffset_t start_;
  void add_local_time_us(int64_t local_time_us) {
    fbb_.AddElement<int64_t>(DepthMessage::VT_LOCAL_TIME_US, local_time_us, 0);
  }
  void add_message(flatbuffers::Offset<DepthUpdate> message) {
    fbb_.AddOffset(DepthMessage::VT_MESSAGE, message);
  }
  explicit DepthMessageBuilder(flatbuffers::FlatBufferBuilder &_fbb)
        : fbb_(_fbb) {
    start_ = fbb_.StartTable();
  }
  flatbuffers::Offset<DepthMessage> Finish() {
    const auto end = fbb_.EndTable(start_);
    auto o = flatbuffers::Offset<DepthMessage>(end);
    return o;
  }
};

inline flatbuffers::Offset<DepthMessage> CreateDepthMessage(
    flatbuffers::FlatBufferBuilder &_fbb,
    int64_t local_time_us = 0,
    flatbuffers::Offset<DepthUpdate> message = 0) {
  DepthMessageBuilder builder_(_fbb);
  builder_.add_local_time_us(local_time_us);
  builder_.add_message(message);
  return builder_.Finish();
}

inline const DepthMessage *GetDepthMessage(const void *buf) {
  return flatbuffers::GetRoot<DepthMessage>(buf);
}

inline const DepthMessage *GetSizePrefixedDepthMessage(const void *buf) {
  return flatbuffers::GetSizePrefixedRoot<DepthMessage>(buf);
}

inline bool VerifyDepthMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifyBuffer<DepthMessage>(nullptr);
}

inline bool VerifySizePrefixedDepthMessageBuffer(
    flatbuffers::Verifier &verifier) {
  return verifier.VerifySizePrefixedBuffer<DepthMessage>(nullptr);
}

inline void FinishDepthMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<DepthMessage> root) {
  fbb.Finish(root);
}

inline void FinishSizePrefixedDepthMessageBuffer(
    flatbuffers::FlatBufferBuilder &fbb,
    flatbuffers::Offset<DepthMessage> root) {
  fbb.FinishSizePrefixed(root);
}

#endif  // FLATBUFFERS_GENERATED_DEPTHMESSAGE_H_
