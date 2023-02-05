#pragma once

#include "inplace_queue.hh"
#include "writer.hh"

#include "cppcuit/circuit.hh"

class Sampler {

  struct WaitingSample {
    std::vector<double> ordered_samples;
    double target;
    std::uint64_t sampled_at;
    std::uint64_t sample_future_at;

    std::strong_ordering operator<=>(const WaitingSample &other) const {
      if (sample_future_at < other.sample_future_at) {
        return std::strong_ordering::less;
      }
      if (sample_future_at > other.sample_future_at) {
        return std::strong_ordering::greater;
      }
      return std::strong_ordering::equal;
    }
  };

  std::shared_ptr<WriterSchema> schema;
  std::unique_ptr<VectorWriter> writer;
  in_place_queue<WaitingSample> waiting_for_future;

  std::vector<OutputHandle<double>> rows_to_sample;
  OutputHandle<double> target;
  OutputHandle<bool> should_sample;

  void clear_top_waiting(const Circuit &circuit);
  void sample_row(std::uint64_t current_time, const Circuit &circuit);

public:
  void examine_waiting(std::uint64_t current_time, const Circuit &circuit) {
    while (waiting_for_future.size() > 0 &&
           waiting_for_future.top().sample_future_at < current_time) {
      clear_top_waiting(circuit);
    }
  }

  void consider_sample(std::uint64_t current_time, const Circuit &circuit) {
    if (circuit.load_from_handle(should_sample).value_or(false)) {
      sample_row(current_time, circuit);
    }
  }

  Sampler(std::shared_ptr<WriterSchema>, std::unique_ptr<VectorWriter>,
          const Circuit &circuit);

  Sampler(Sampler &&) = default;
  Sampler &operator=(Sampler &&) = default;
};