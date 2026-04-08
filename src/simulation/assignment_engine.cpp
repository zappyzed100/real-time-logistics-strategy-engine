#include <cstdint>

namespace {

inline bool is_assigned(const std::uint64_t* assigned_bits, const std::int32_t order_index) {
    return (assigned_bits[order_index >> 6] & (std::uint64_t{1} << (order_index & 63))) != 0;
}

inline void mark_assigned(std::uint64_t* assigned_bits, const std::int32_t order_index) {
    assigned_bits[order_index >> 6] |= (std::uint64_t{1} << (order_index & 63));
}

}  // namespace

extern "C" int run_assignment_engine(
    const std::int32_t order_count,
    const std::int32_t center_count,
    const std::int32_t candidate_count,
    const std::int32_t orders_per_staff,
    const std::int32_t staffing_round_increment,
    const std::int32_t* ranked_center_indices,
    const std::int32_t* center_staffing_levels,
    const std::int32_t* center_candidate_offsets,
    const std::int32_t* candidate_order_indices,
    const std::int32_t* candidate_center_indices,
    const double* candidate_distance_km,
    const double* candidate_delivery_cost,
    std::int32_t* out_assigned_center_indices,
    double* out_assigned_distance_km,
    double* out_assigned_delivery_cost,
    std::uint8_t* out_is_assigned
) {
    if (order_count < 0 || center_count <= 0 || candidate_count < 0) {
        return -1;
    }
    if (orders_per_staff <= 0 || staffing_round_increment <= 0) {
        return -2;
    }

    const std::int32_t bit_word_count = (order_count + 63) >> 6;
    auto assigned_bits = new std::uint64_t[bit_word_count > 0 ? bit_word_count : 1]();

    std::int32_t max_staffing_level = 0;
    for (std::int32_t center_index = 0; center_index < center_count; ++center_index) {
        if (center_staffing_levels[center_index] > max_staffing_level) {
            max_staffing_level = center_staffing_levels[center_index];
        }
    }

    for (std::int32_t current_staff_floor = 0;
         current_staff_floor < max_staffing_level;
         current_staff_floor += staffing_round_increment) {
        for (std::int32_t ranked_index = 0; ranked_index < center_count; ++ranked_index) {
            const std::int32_t center_index = ranked_center_indices[ranked_index];
            const std::int32_t staffing_level = center_staffing_levels[center_index];
            if (staffing_level <= current_staff_floor) {
                continue;
            }

            const std::int32_t active_staff_in_round =
                staffing_round_increment < (staffing_level - current_staff_floor)
                    ? staffing_round_increment
                    : (staffing_level - current_staff_floor);
            const std::int32_t assignment_limit = active_staff_in_round * orders_per_staff;
            std::int32_t assigned_in_round = 0;

            for (std::int32_t candidate_index = center_candidate_offsets[center_index];
                 candidate_index < center_candidate_offsets[center_index + 1];
                 ++candidate_index) {
                const std::int32_t order_index = candidate_order_indices[candidate_index];
                if (is_assigned(assigned_bits, order_index)) {
                    continue;
                }

                mark_assigned(assigned_bits, order_index);
                out_is_assigned[order_index] = 1;
                out_assigned_center_indices[order_index] = candidate_center_indices[candidate_index];
                out_assigned_distance_km[order_index] = candidate_distance_km[candidate_index];
                out_assigned_delivery_cost[order_index] = candidate_delivery_cost[candidate_index];
                ++assigned_in_round;
                if (assigned_in_round >= assignment_limit) {
                    break;
                }
            }
        }
    }

    delete[] assigned_bits;
    return 0;
}