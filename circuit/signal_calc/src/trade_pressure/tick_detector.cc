#include "math/fast_exp_64.hh"
#include "trade_pressure/tick_detector.hh"

#include <nlohmann/json.hpp>

void TickCompletionDetector::schedule_invalidation_at(std::uint64_t invalidate_at, TimerHandle reschedule) {
  is_invalidation_scheduled = true;
  reschedule.schedule_call_at(invalidate_at);
}


void TickCompletionDetector::do_init(const nlohmann::json &params) {
  us_till_batch_ends = params["us_till_batch_ends"].get<double>();
  ns_till_batch_invalidation = params["ns_till_batch_invalidation"].get<double>();
}