# docker run --rm -it -v /home/wiktor/ont-str-code/img:/home/wiktor/ont-str-code/img -w /home/wiktor/ont-str-code/img nanozoo/ggplot2:3.4.0--4856650 R

library(ggplot2)
library(viridis)

# https://42basepairs.com/browse/s3/ont-open-data/giab_2025.01/analysis/wf-human-variation/hac/HG002/PAW71238/output
# plik SAMPLE.wf-human-str-report.html

# hac HG001 PAW79146 HTT 20.3 16
# hac HG001 PAW81754 HTT 20.3 16
# hac HG002 PAW70337 HTT 24 17
# hac HG002 PAW71238 HTT 24 17
# hac HG003 PAY87794 HTT 17 17
# hac HG003 PAY87954 HTT 17 13
# hac HG004 PAY87778 HTT 24 17
# hac HG004 PAY88428 HTT 23.7 17
# hac HG005 PAW87816 HTT 18 16
# hac HG005 PAW88001 HTT 18 18
# hac HG006 PAY77227 HTT 17 17
# hac HG006 PBA16846 HTT 17 13
# hac HG007 PAY12990 HTT 17 17
# hac HG007 PBA20413 HTT 17 14.7

# sup HG001 PAW79146 HTT 20.3 16
# sup HG001 PAW81754 HTT 20.3 16
# sup HG002 PAW70337 HTT 24 17
# sup HG002 PAW71238 HTT 24 17
# sup HG003 PAY87794 HTT 17 12.7
# sup HG003 PAY87954 HTT 17 10.3
# sup HG004 PAY87778 HTT 24 17
# sup HG004 PAY88428 HTT 17 8.4
# sup HG005 PAW87816 HTT 18 18
# sup HG005 PAW88001 HTT 18 15.7
# sup HG006 PAY77227 HTT 17 17
# sup HG006 PBA16846 HTT 18 13.7
# sup HG007 PAY12990 HTT 17 17
# sup HG007 PBA20413 HTT 18 14.6

bench <- c(17,72,17,18,17,40,20,41,21,41,18,41,18,40,21,41,18,39,17,57,18,40,26,46)
deeprepeat <- c(17,69,18,20,19,41,23,42,23,42,21,42,20,41,19,42,20,40,19,57,20,41,28,47)
strique <- c(16,72,18,19,18,42,23,44,22,43,20,43,19,43,18,43,19,42,18,59,19,42,28,48)
warpstr <- c(15,70,17,17,17,40,21,42,21,41,19,41,18,40,17,41,18,39,17,57,18,40,26,46)
ontstr <- c(17,72,17,18,17,40,20,41,21,41,18,41,18,40,21,41,18,39,17,57,18,40,26,46)  # TODO wyniki mojej aplikacji

Application <- c(rep("DeepRepeat",24),rep("STRique",24),rep("WarpSTR",24),rep("ONTstr",24))
estimated <- c(deeprepeat,strique,warpstr,ontstr)
benchmark <- rep(bench, 4)
estimated_minus_benchmark <- estimated - benchmark
data <- data.frame(Application, estimated, benchmark, estimated_minus_benchmark)
print(data)

p <- ggplot(data, aes(x=benchmark, y=estimated, color=Application)) + xlab("Benchmark repeat counts") + ylab("Estimated repeat counts") + geom_point() + geom_abline(intercept = 0, slope = 1) + scale_y_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) + scale_x_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) + theme(legend.position="bottom",plot.tag=element_text(size=36,face="bold")) + labs(tag="A")
ggsave("estimated_vs_benchmark.svg")
# inkscape estimated_vs_benchmark.svg --export-pdf=estimated_vs_benchmark.pdf

p <- ggplot(data, aes(x=benchmark, y=estimated_minus_benchmark, color=Application)) + xlab("Benchmark repeat counts") + ylab("Estimated - Benchmark") + geom_point() + geom_abline(intercept = 0, slope = 0) + scale_y_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) + scale_x_continuous(breaks = function(x) unique(floor(pretty(seq(min(x), (max(x) + 1) * 1.1))))) + theme(legend.position="bottom",plot.tag=element_text(size=36,face="bold")) + labs(tag="B")
ggsave("estimated_minus_benchmark.svg")
# inkscape estimated_minus_benchmark.svg --export-pdf=estimated_minus_benchmark.pdf
