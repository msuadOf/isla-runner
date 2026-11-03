function review_probe(a : bits(32)) -> bits(32) = fp32_to_ieee(fp32_add(round_nearest_ties_to_even(), fp32_from_ieee(a), fp32_from_ieee(a)))
