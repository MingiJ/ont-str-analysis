# docker run --rm -it -v /home/wiktor/ont-str-code/img:/home/wiktor/ont-str-code/img -w /home/wiktor/ont-str-code/img nanozoo/ggplot2:3.4.0--4856650 R

library(ggplot2)
library(viridis)

# GM04723.tar.gz.1 17,72
# NA12878.tar.gz.1 17,18
# ND29970.tar.gz.1 17,40
# ND30015.tar.gz.1 20,41
# ND30016.tar.gz.1 21,41
# ND30047.tar.gz.1 18,41
# ND30422.tar.gz.1 18,40
# ND30626.tar.gz.1 21,41
# ND31551.tar.gz.1 18,39
# ND33392.tar.gz.1 17,57
# ND33947.tar.gz.1 18,40
# ND40534.tar.gz.1 26,46

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
