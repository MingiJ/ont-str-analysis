svg_stack.py --direction=h --margin=100 estimated_vs_benchmark.svg estimated_minus_benchmark.svg > hd_img_1_row.svg
svg_stack.py --direction=h --margin=100 repeat_count_distribution_NA12878.svg repeat_count_distribution_ND33392.svg > hd_img_2_row.svg

svg_stack.py --direction=v --margin=100 hd_img_1_row.svg hd_img_2_row.svg > hd_img.svg

convert hd_img.svg hd_img.png
