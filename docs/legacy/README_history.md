# ont-str-code (archived notes)

===============================================
================ warpstr ======================
===============================================
musi mieć pliki muliti fast5, a nie single
single_to_multi_fast5 -i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 -s /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass_multi/0
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wiktor/ont-str/warpstr/config.yaml

===============================================
============== deeprepeat =====================
===============================================
wget https://www.openbioinformatics.org/hx1/drmodel/trainedmod_32_0.2.tar.gz
tar -xvf trainedmod_32_0.2.tar.gz      -- jest na eve w /export
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND33392 --is_pcr 0 --repeatName ND33392_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/ND33392.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND33392.log 2>&1
grep "GMM:" ND33392.log


===============================================
================ strique ======================
===============================================
cd /home/wiktor/ont-str
samtools view -h -o ND33392.sam' ND33392.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 > /home/wiktor/ont-str/strique/ND33392.fofn
usunąć kilka pierwszych linijek z /home/wiktor/ont-str/strique/ND33392.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND33392.txt --algn /home/wiktor/ont-str/ND33392.sam' --log_level debug /home/wiktor/ont-str/strique/ND33392.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv   -- czy suffix i prefix są odpowiednio długie????????


===============================================
=============== 12 HTT samples ================
===============================================
GM04723
NA12878
ND29970
ND30015
ND30016
ND30047
ND30422
ND30626
ND31551
ND33392
ND33947
ND40534

docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/GM04723/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/GM04723/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND29970/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND29970/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30015/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30015/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30016/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30016/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30047/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30047/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30422/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30422/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30626/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30626/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND31551/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND31551/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33947/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33947/workspace/pass_multi/0
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str ttubb/ont-fast5-api:latest single_to_multi_fast5 -i /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND40534/workspace/pass/0 -s /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND40534/workspace/pass_multi/0

docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_GM04723.yaml
Caller time: 38324587 ms, Samples called: 264682457, samples/s: 6906.34
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_GM04723/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_GM04723/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_GM04723/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_GM04723/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (243, 87)
Allele lengths as given by basecall: (234, 85)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    70    15
Unit: CGC        Repeats:     7    10
There were 2013 reads for allele1 and 1678 for allele2
  Duration for whole: 25h 21m 90014s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_NA12878.yaml
Caller time: 20685496 ms, Samples called: 141741575, samples/s: 6852.22
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_NA12878/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_NA12878/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_NA12878/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_NA12878/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (90, '-')
Allele lengths as given by basecall: (84, '-')
Genotyped complex repeats in a homozygous allele:
Unit: AGC        Repeats:    17 -
Unit: CGC        Repeats:     9 -
There were 1941 reads for allele1 and - for allele2
  Duration for whole: 12h 22m 43211s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND29970.yaml
Caller time: 38006655 ms, Samples called: 264620463, samples/s: 6962.48
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND29970/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND29970/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND29970/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND29970/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (153, 93)
Allele lengths as given by basecall: (149, 91)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    40    17
Unit: CGC        Repeats:     7    10
There were 2230 reads for allele1 and 1524 for allele2
  Duration for whole: 20h 27m 72010s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND30015.yaml
Caller time: 20878874 ms, Samples called: 173881995, samples/s: 8328.13
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND30015/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND30015/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND30015/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND30015/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (159, 105)
Allele lengths as given by basecall: (153, 103)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    42    21
Unit: CGC        Repeats:     7    10
There were 1258 reads for allele1 and 1134 for allele2
  Duration for whole: 11h 36m 39642s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND30016.yaml
Caller time: 31405033 ms, Samples called: 266807779, samples/s: 8495.7
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND30016/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND30016/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND30016/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND30016/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (156, 105)
Allele lengths as given by basecall: (152, 102)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    41    21
Unit: CGC        Repeats:     7    10
There were 2318 reads for allele1 and 1428 for allele2
  Duration for whole: 17h 48m 61229s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND30047.yaml
Caller time: 33288313 ms, Samples called: 284136351, samples/s: 8535.62
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND30047/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND30047/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND30047/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND30047/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (156, 99)
Allele lengths as given by basecall: (152, 96)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    41    19
Unit: CGC        Repeats:     7    10
There were 2269 reads for allele1 and 1707 for allele2
  Duration for whole: 18h 30m 64838s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND30422.yaml
Caller time: 31894841 ms, Samples called: 272011012, samples/s: 8528.37
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND30422/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND30422/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND30422/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND30422/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (153, 96)
Allele lengths as given by basecall: (148, 93)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    40    18
Unit: CGC        Repeats:     7    10
There were 2352 reads for allele1 and 1399 for allele2
  Duration for whole: 17h 51m 61214s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND30626.yaml
Caller time: 30781032 ms, Samples called: 261475463, samples/s: 8494.69
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND30626/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND30626/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND30626/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND30626/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (156, 84)
Allele lengths as given by basecall: (152, 82)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    41    17
Unit: CGC        Repeats:     7     7
There were 2199 reads for allele1 and 1528 for allele2
  Duration for whole: 17h 17m 61208s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND31551.yaml
Caller time: 20884507 ms, Samples called: 172938103, samples/s: 8280.69
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND31551/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND31551/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND31551/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND31551/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (90, 162)
Allele lengths as given by basecall: (85, 154)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    18    39
Unit: CGC        Repeats:     8    10
There were 1572 reads for allele1 and 768 for allele2
  Duration for whole: 11h 11m 39618s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND33392.yaml
Caller time: 31194452 ms, Samples called: 265299859, samples/s: 8504.71
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND33392/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND33392/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND33392/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND33392/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (204, 93)
Allele lengths as given by basecall: (198, 90)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    57    17
Unit: CGC        Repeats:     7    10
There were 2055 reads for allele1 and 1640 for allele2
  Duration for whole: 17h 48m 61251s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND33947.yaml
Caller time: 23843034 ms, Samples called: 199776730, samples/s: 8378.83
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND33947/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND33947/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND33947/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND33947/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (96, 153)
Allele lengths as given by basecall: (94, 150)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    18    40
Unit: CGC        Repeats:    10     7
There were 1383 reads for allele1 and 1370 for allele2
  Duration for whole: 13h 08m 46834s
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 python3.7 /opt/warpstr/WarpSTR.py /home/wkusmirek/ont-str/warpstr/config_ND40534.yaml
Caller time: 33601281 ms, Samples called: 286250340, samples/s: 8519.03
Finishing up any open output files.
Basecalling completed successfully.
find /home/wkusmirek/ont-str/warpstr/HD_ND40534/fast5/pass_multi/aux/workspace -maxdepth 1 -name *.fast5 -print0 | xargs  -0 cp -t /home/wkusmirek/ont-str/warpstr/HD_ND40534/fast5/pass_multi/annot;
Finished Guppy basecalling for /home/wkusmirek/ont-str/warpstr/HD_ND40534/fast5/pass_multi
DEBUG_3_TREX: Extracting TRs - running with 1 threads
 Results stored in overview file /home/wkusmirek/ont-str/warpstr/HD_ND40534/overview.csv
Running complex genotyping as complex repeat units present: ['(AGC)', '(CGC)']
Allele lengths as given by WarpSTR: (171, 111)
Allele lengths as given by basecall: (167, 108)
Genotyped complex repeats in 2 alleles:
Unit: AGC        Repeats:    46    26
Unit: CGC        Repeats:     7     7
There were 2077 reads for allele1 and 1877 for allele2
  Duration for whole: 19h 04m 68440s
  
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '0' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '1' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '2' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '3' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '4' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '5' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '6' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '7' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '8' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '9' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '10' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '11' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '12' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '13' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '14' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '15' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '16' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '17' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '18' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '19' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '20' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '21' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '22' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '23' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '24' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '25' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '26' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '27' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '28' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '29' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '30' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '31' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '32' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '33' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '34' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '35' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '36' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '37' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '38' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '39' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '40' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '41' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '42' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '43' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '44' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '45' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '46' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '47' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '48' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '49' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '50' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '51' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '52' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '53' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '54' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '55' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '56' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '57' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '58' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '59' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '60' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '61' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '62' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '63' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '64' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '65' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '66' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '67' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '68' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '69' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '70' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '71' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '72' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '73' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '74' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '75' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '76' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '77' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '78' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '79' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '80' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '81' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '82' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '83' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '84' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '85' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '86' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '87' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '88' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '89' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '90' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '91' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '92' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '93' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '94' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '95' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '96' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '97' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '98' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '99' | wc -l
awk -F "\"*,\"*" '{print $2}' /home/wkusmirek/ont-str/warpstr/HD_GM04723/predictions/complexSTR_analysis/complex_repeat_units.csv | grep -w '100' | wc -l

GM04723
NA12878
ND29970
ND30015
ND30016
ND30047
ND30422
ND30626
ND31551
ND33392
ND33947
ND40534

docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/GM04723/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/GM04723/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/NA12878/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND29970/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND29970/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30015/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30015/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30016/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30016/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30047/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30047/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30422/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30422/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30626/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND30626/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND31551/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND31551/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33392/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33947/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND33947/workspace/pass_multi
docker run --rm -it -v /home/wkusmirek/ont-str:/home/wkusmirek/ont-str wkusmirek/warpstr:0.3.2 cp /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND40534/*bam* /home/wkusmirek/ont-str/dataset/hd-deeprepeat/ND40534/workspace/pass_multi

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID GM04723 --is_pcr 0 --repeatName GM04723_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/GM04723.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/htt.f5index --rpg /app/data/wg_trf.cag.bed > GM04723.log 2>&1
grep "GMM:" GM04723.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID NA12878 --is_pcr 0 --repeatName NA12878_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/NA12878.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/htt.f5index --rpg /app/data/wg_trf.cag.bed > NA12878.log 2>&1
grep "GMM:" NA12878.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND29970 --is_pcr 0 --repeatName ND29970_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/ND29970.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND29970.log 2>&1
grep "GMM:" ND29970.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND30015 --is_pcr 0 --repeatName ND30015_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/ND30015.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND30015.log 2>&1
grep "GMM:" ND30015.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND30016 --is_pcr 0 --repeatName ND30016_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/ND30016.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND30016.log 2>&1
grep "GMM:" ND30016.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND30047 --is_pcr 0 --repeatName ND30047_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/ND30047.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND30047.log 2>&1
grep "GMM:" ND30047.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND30422 --is_pcr 0 --repeatName ND30422_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/ND30422.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND30422.log 2>&1
grep "GMM:" ND30422.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND30626 --is_pcr 0 --repeatName ND30626_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/ND30626.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND30626.log 2>&1
grep "GMM:" ND30626.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND31551 --is_pcr 0 --repeatName ND31551_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/ND31551.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND31551.log 2>&1
grep "GMM:" ND31551.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND33392 --is_pcr 0 --repeatName ND33392_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/ND33392.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND33392.log 2>&1
grep "GMM:" ND33392.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND33947 --is_pcr 0 --repeatName ND33947_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/ND33947.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND33947.log 2>&1
grep "GMM:" ND33947.log
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/deeprepeat genomicslab/deeprepeat:0.1.3 DeepRepeat.py Detect --gn CAG_htt2_90 --TempRem 0 --epchon 50 --repeat_relax_bp 15 --UniqueID ND40534 --is_pcr 0 --repeatName ND40534_htt --repeat chr4:3074876-3074933:CAG:3 --o /home/wiktor/ont-str/deeprepeat --bam /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/ND40534.bam --f5folder /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534 --algLen 100 --f5i /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/htt.f5index --rpg /app/data/wg_trf.cag.bed > ND40534.log 2>&1
grep "GMM:" ND40534.log

samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/GM04723.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/GM04723.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/NA12878.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/NA12878.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/ND29970.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/ND29970.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/ND30015.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/ND30015.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/ND30016.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/ND30016.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/ND30047.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/ND30047.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/ND30422.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/ND30422.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/ND30626.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/ND30626.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/ND31551.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/ND31551.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/ND33392.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/ND33392.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/ND33947.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/ND33947.bam
samtools view -h -o /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/ND40534.sam' /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/ND40534.bam

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/workspace/pass/0 > /home/wiktor/ont-str/strique/GM04723.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 > /home/wiktor/ont-str/strique/NA12878.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/workspace/pass/0 > /home/wiktor/ont-str/strique/ND29970.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/workspace/pass/0 > /home/wiktor/ont-str/strique/ND30015.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/workspace/pass/0 > /home/wiktor/ont-str/strique/ND30016.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/workspace/pass/0 > /home/wiktor/ont-str/strique/ND30047.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/workspace/pass/0 > /home/wiktor/ont-str/strique/ND30422.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/workspace/pass/0 > /home/wiktor/ont-str/strique/ND30626.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/workspace/pass/0 > /home/wiktor/ont-str/strique/ND31551.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 > /home/wiktor/ont-str/strique/ND33392.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/workspace/pass/0 > /home/wiktor/ont-str/strique/ND33947.fofn
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py index --recursive --out_prefix /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/workspace/pass/0/ /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/workspace/pass/0 > /home/wiktor/ont-str/strique/ND40534.fofn

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/GM04723.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/GM04723/GM04723.sam' --log_level debug /home/wiktor/ont-str/strique/GM04723.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/NA12878.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/NA12878.sam' --log_level debug /home/wiktor/ont-str/strique/NA12878.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND29970.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND29970/ND29970.sam' --log_level debug /home/wiktor/ont-str/strique/ND29970.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND30015.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30015/ND30015.sam' --log_level debug /home/wiktor/ont-str/strique/ND30015.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND30016.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30016/ND30016.sam' --log_level debug /home/wiktor/ont-str/strique/ND30016.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND30047.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30047/ND30047.sam' --log_level debug /home/wiktor/ont-str/strique/ND30047.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND30422.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30422/ND30422.sam' --log_level debug /home/wiktor/ont-str/strique/ND30422.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND30626.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND30626/ND30626.sam' --log_level debug /home/wiktor/ont-str/strique/ND30626.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND31551.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND31551/ND31551.sam' --log_level debug /home/wiktor/ont-str/strique/ND31551.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND33392.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/ND33392.sam' --log_level debug /home/wiktor/ont-str/strique/ND33392.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND33947.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33947/ND33947.sam' --log_level debug /home/wiktor/ont-str/strique/ND33947.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str giesselmann/strique:v0.4.2 python3 /app/scripts/STRique.py count --out /home/wiktor/ont-str/strique/ND40534.txt --algn /home/wiktor/ont-str/dataset/hd-deeprepeat/ND40534/ND40534.sam' --log_level debug /home/wiktor/ont-str/strique/ND40534.fofn /app/models/r9_4_450bps.model /home/wiktor/ont-str/strique/config.tsv

grep -P '\t0\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t1\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t2\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t3\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t4\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t5\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t6\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t7\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t8\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t9\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t10\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t11\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t12\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t13\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t14\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t15\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t16\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t17\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t18\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t19\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t20\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t21\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t22\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t23\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t24\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t25\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t26\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t27\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t28\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t29\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t30\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t31\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t32\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t33\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t34\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t35\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t36\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t37\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t38\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t39\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t40\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t41\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t42\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t43\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t44\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t45\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t46\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t47\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t48\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t49\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t50\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t51\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t52\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t53\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t54\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t55\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t56\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t57\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t58\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t59\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t60\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t61\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t62\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t63\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t64\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t65\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t66\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t67\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t68\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t69\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t70\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t71\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t72\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t73\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t74\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t75\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t76\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t77\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t78\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t79\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t80\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t81\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t82\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t83\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t84\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t85\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t86\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t87\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t88\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t89\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t90\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t91\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t92\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t93\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t94\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t95\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t96\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t97\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t98\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t99\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l
grep -P '\t100\t' /home/wiktor/ont-str/strique/ND30422.txt | wc -l

===============================================
============== GIAB R10.4 =====================
===============================================
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr1:149390803-149390841" > hac/NOTCH2NLC.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr2:190880873-190880920" > hac/GLS.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr3:63912685-63912714" > hac/ATXN7.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr3:63912715-63912726" > hac/ATXN7_GCC.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr3:129172577-129172656" > hac/CNBP.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr3:129172657-129172696" > hac/CNBP_CAGA.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr3:129172697-129172732" > hac/CNBP_CA.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr4:3074877-3074933" > hac/HTT.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr4:3074940-3074966" > hac/HTT_CCG.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr4:39348425-39348479" > hac/RFC1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr4:41745973-41746032" > hac/PHOX2B.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr5:146878728-146878757" > hac/PPP2R2B.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr6:16327634-16327723" > hac/ATXN1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr6:170561907-170562017" > hac/TBP.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr8:104588968-104588999" > hac/LRP12.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr9:27573529-27573546" > hac/C9ORF72.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr9:69037287-69037304" > hac/FXN.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr12:6936717-6936773" > hac/ATN1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr12:50505002-50505022" > hac/DIP2B.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr12:111598950-111599018" > hac/ATXN2.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr13:70139354-70139383" > hac/ATXN8OS_CTA.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr13:70139354-70139383" > hac/ATXN8OS.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr14:23321473-23321490" > hac/PABPN1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr14:92071010-92071042" > hac/ATXN3.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr15:22786678-22786701" > hac/NIPA1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr16:87604288-87604329" > hac/JPH3.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr18:55586156-55586227" > hac/TCF4.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr19:13207859-13207897" > hac/CACNA1A.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr19:14496042-14496074" > hac/GIPC1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr19:45770205-45770264" > hac/DMPK.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr20:2652734-2652757" > hac/NOP56.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr20:2652758-2652775" > hac/NOP56_CGCCTG.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr21:43776444-43776479" > hac/CSTB.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chr22:45795355-45795424" > hac/ATXN10.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chrX:67545317-67545385" > hac/AR.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chrX:147912051-147912110" > hac/FMR1.sam'
docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools view hac/calls.sorted.bam "chrX:148500632-148500691" > hac/AFF2.sam'

cut -f1 NOTCH2NLC.sam | sort | uniq > NOTCH2NLC_read_ids.txt
cut -f1 GLS.sam | sort | uniq > GLS_read_ids.txt
cut -f1 ATXN7.sam | sort | uniq > ATXN7_read_ids.txt
cut -f1 ATXN7_GCC.sam | sort | uniq > ATXN7_GCC_read_ids.txt
cut -f1 CNBP.sam | sort | uniq > CNBP_read_ids.txt
cut -f1 CNBP_CAGA.sam | sort | uniq > CNBP_CAGA_read_ids.txt
cut -f1 CNBP_CA.sam | sort | uniq > CNBP_CA_read_ids.txt
cut -f1 HTT.sam | sort | uniq > HTT_read_ids.txt
cut -f1 HTT_CCG.sam | sort | uniq > HTT_CCG_read_ids.txt
cut -f1 RFC1.sam | sort | uniq > RFC1_read_ids.txt
cut -f1 PHOX2B.sam | sort | uniq > PHOX2B_read_ids.txt
cut -f1 PPP2R2B.sam | sort | uniq > PPP2R2B_read_ids.txt
cut -f1 ATXN1.sam | sort | uniq > ATXN1_read_ids.txt
cut -f1 TBP.sam | sort | uniq > TBP_read_ids.txt
cut -f1 LRP12.sam | sort | uniq > LRP12_read_ids.txt
cut -f1 C9ORF72.sam | sort | uniq > C9ORF72_read_ids.txt
cut -f1 FXN.sam | sort | uniq > FXN_read_ids.txt
cut -f1 ATN1.sam | sort | uniq > ATN1_read_ids.txt
cut -f1 DIP2B.sam | sort | uniq > DIP2B_read_ids.txt
cut -f1 ATXN2.sam | sort | uniq > ATXN2_read_ids.txt
cut -f1 ATXN8OS_CTA.sam | sort | uniq > ATXN8OS_CTA_read_ids.txt
cut -f1 ATXN8OS.sam | sort | uniq > ATXN8OS_read_ids.txt
cut -f1 PABPN1.sam | sort | uniq > PABPN1_read_ids.txt
cut -f1 ATXN3.sam | sort | uniq > ATXN3_read_ids.txt
cut -f1 NIPA1.sam | sort | uniq > NIPA1_read_ids.txt
cut -f1 JPH3.sam | sort | uniq > JPH3_read_ids.txt
cut -f1 TCF4.sam | sort | uniq > TCF4_read_ids.txt
cut -f1 CACNA1A.sam | sort | uniq > CACNA1A_read_ids.txt
cut -f1 GIPC1.sam | sort | uniq > GIPC1_read_ids.txt
cut -f1 DMPK.sam | sort | uniq > DMPK_read_ids.txt
cut -f1 NOP56.sam | sort | uniq > NOP56_read_ids.txt
cut -f1 NOP56_CGCCTG.sam | sort | uniq > NOP56_CGCCTG_read_ids.txt
cut -f1 CSTB.sam | sort | uniq > CSTB_read_ids.txt
cut -f1 ATXN10.sam | sort | uniq > ATXN10_read_ids.txt
cut -f1 AR.sam | sort | uniq > AR_read_ids.txt
cut -f1 FMR1.sam | sort | uniq > FMR1_read_ids.txt
cut -f1 AFF2.sam | sort | uniq > AFF2_read_ids.txt

docker run --rm -it -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/samtools:1.21 bash -c 'samtools fastq hac/sam/calls.sorted.bam > hac/fastq/calls.sorted.fastq'

bash
for s in NOTCH2NLC GLS ATXN7 ATXN7_GCC CNBP CNBP_CAGA CNBP_CA HTT HTT_CCG RFC1 PHOX2B PPP2R2B ATXN1 TBP LRP12 C9ORF72 FXN ATN1 DIP2B ATXN2 ATXN8OS_CTA ATXN8OS PABPN1 ATXN3 NIPA1 JPH3 TCF4 CACNA1A GIPC1 DMPK NOP56 NOP56_CGCCTG CSTB ATXN10 AR FMR1 AFF2; do
    docker run --rm -it -e s=${s} -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/seqtk:1.4 bash -c 'seqtk subseq hac/fastq/calls.sorted.fastq hac/read_ids/${s}_read_ids.txt > fastq_filtered/${s}_hac.fastq'
done;

bash
for s in NOTCH2NLC GLS ATXN7 ATXN7_GCC CNBP CNBP_CAGA CNBP_CA HTT HTT_CCG RFC1 PHOX2B PPP2R2B ATXN1 TBP LRP12 C9ORF72 FXN ATN1 DIP2B ATXN2 ATXN8OS_CTA ATXN8OS PABPN1 ATXN3 NIPA1 JPH3 TCF4 CACNA1A GIPC1 DMPK NOP56 NOP56_CGCCTG CSTB ATXN10 AR FMR1 AFF2; do
    docker run --rm -it -e POD5_DEBUG=1 -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/pod5:0.3.23 pod5 filter --output pod5_filtered/${s}_hac.pod5 --ids hac/read_ids/${s}_read_ids.txt --missing-ok pod5/*.pod5
done;

bash
for s in NOTCH2NLC GLS ATXN7 ATXN7_GCC CNBP CNBP_CAGA CNBP_CA HTT HTT_CCG RFC1 PHOX2B PPP2R2B ATXN1 TBP LRP12 C9ORF72 FXN ATN1 DIP2B ATXN2 ATXN8OS_CTA ATXN8OS PABPN1 ATXN3 NIPA1 JPH3 TCF4 CACNA1A GIPC1 DMPK NOP56 NOP56_CGCCTG CSTB ATXN10 AR FMR1 AFF2; do
    docker run --rm -it -e POD5_DEBUG=1 -v /home/ubuntu/workdir/data:/home/ubuntu/workdir/data -w /home/ubuntu/workdir/data/HG002/PAW70337 staphb/pod5:0.3.23 pod5 convert to_fast5 pod5_filtered/${s}_hac.pod5 --output fast5_filtered
done;

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str btrspg/slow5tools:dev slow5tools f2s /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered -d /home/wiktor/ont-str/dataset/hg002/hac/blow5_filtered --allow

cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/HTT_hac.fastq | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/HTT_hac.fastq
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/HTT_hac.fastq -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hg002/hac/blow5_filtered/HTT_hac.0_0.blow5 --min-mapq 0 -o eventalign_reads_hg002_hac_HTT.tsv --min-recalib-events 5 --print-read-names --scale-events --samples
cd /home/wiktor/ont-str-code
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_hg002_hac_HTT.tsv --region chr4:3074870-3074933 --kmer_model extern/kmer_models/dna_r10.4.1_e8.2_400bps/9mer_levels_v1.txt --kmer_length 9 --motif CAG --min_motif_repeat_counts 1 --max_motif_repeat_counts 200 --results /home/wiktor/ont-str-code/results-hg002-hac-HTT

cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/RFC1_hac.fastq | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/RFC1_hac.fastq
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/RFC1_hac.fastq -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hg002/hac/blow5_filtered/RFC1_hac.0_0.blow5 --min-mapq 0 -o eventalign_reads_hg002_hac_RFC1.tsv --min-recalib-events 5 --print-read-names --scale-events --samples
cd /home/wiktor/ont-str-code
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_hg002_hac_RFC1.tsv --region chr4:39348425-39348470 --kmer_model extern/kmer_models/dna_r10.4.1_e8.2_400bps/9mer_levels_v1.txt --kmer_length 9 --motif AAAAG --min_motif_repeat_counts 1 --max_motif_repeat_counts 200 --results /home/wiktor/ont-str-code/results-hg002-hac-RFC1

dla tego się nie uda, bo on ma nie taki sam motyw, GCTgccgccgctgccgctgccgccgccgccgctgccgcggccgccgccgcTGCTGCTGCG, poniżej na pewno błędne współrzędne!!!
cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/PHOX2B_hac.fastq | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/PHOX2B_hac.fastq
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hg002/hac/fastq_filtered/PHOX2B_hac.fastq -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hg002/hac/blow5_filtered/PHOX2B_hac.0_0.blow5 --min-mapq 0 -o eventalign_reads_hg002_hac_PHOX2B.tsv --min-recalib-events 5 --print-read-names --scale-events --samples
cd /home/wiktor/ont-str-code
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hg002/hac/fast5_filtered --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_hg002_hac_PHOX2B.tsv --region chr4:39348425-39348470 --kmer_model extern/kmer_models/dna_r10.4.1_e8.2_400bps/9mer_levels_v1.txt --kmer_length 9 --motif GCC --min_motif_repeat_counts 1 --max_motif_repeat_counts 200 --results /home/wiktor/ont-str-code/results-hg002-hac-PHOX2B

===============================================
=============== scrappie ======================
===============================================
/home/wiktor/scrappie/build/scrappie event_table /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0/GXB01181_20181017_FAK03624_GA20000_sequencing_run_HTTdisease12Sample_45241_read_13789_ch_467_strand.fast5

====================================================
========== sigmap fast5 to fastq ===================
====================================================
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/sigmap wkusmirek/sigmap /app/sigmap -i -r /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/1ebea0d2-adbb-44f4-a268-c48f4caacf1a.fa -p /app/extern/kmer_models/r9.4_180mv_450bps_6mer/template_median68pA.model -o 1ebea0d2-adbb-44f4-a268-c48f4caacf1a_index

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/sigmap wkusmirek/sigmap /app/sigmap --map --ref /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/1ebea0d2-adbb-44f4-a268-c48f4caacf1a.fa --pore-model /app/extern/kmer_models/r9.4_180mv_450bps_6mer/template_median68pA.model --ref-index 1ebea0d2-adbb-44f4-a268-c48f4caacf1a_index --sig-dir /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/fast5_subset --output result.paf --num-threads 4

====================================================
=== sigmap fast5 to fasta with another morifs ======
====================================================
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/sigmap wkusmirek/sigmap /app/sigmap -i -r /home/wiktor/ont-str/dataset/hd/chr4_another_motifs.fa -p /app/extern/kmer_models/r9.4_180mv_450bps_6mer/template_median68pA.model -o chr4_another_motifs_index

docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str/sigmap wkusmirek/sigmap /app/sigmap --map --ref /home/wiktor/ont-str/dataset/hd/chr4_another_motifs.fa --pore-model /app/extern/kmer_models/r9.4_180mv_450bps_6mer/template_median68pA.model --ref-index chr4_another_motifs_index --sig-dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --output result.paf --num-threads 4

====================================================
================ slow5 ========================
====================================================
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str btrspg/slow5tools:dev slow5tools f2s /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 -d /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/blow5 --allow
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str btrspg/slow5tools:dev slow5tools cat /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/blow5 -o /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/reads.blow5

====================================================
================ eventalign ========================
====================================================
cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/1ebea0d2-adbb-44f4-a268-c48f4caacf1a.fa | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/fast5_subset /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/1ebea0d2-adbb-44f4-a268-c48f4caacf1a.fa
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/1ebea0d2-adbb-44f4-a268-c48f4caacf1a.fa -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/reads.blow5 ---min-mapq 0 -o eventalign_reads.tsv --min-recalib-events 5 --print-read-names --scale-events --samples

cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/NA12878.fq | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/NA12878.fq
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/NA12878.fq -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/reads.blow5 ---min-mapq 0 -o eventalign_reads_NA12878.tsv --min-recalib-events 5 --print-read-names --scale-events --samples

cd /home/wiktor/ont-str
bwa mem -W13 -k6 -xont2d -T20 /home/wiktor/ont-str/dataset/hd/chr4.fa /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/ND33392.fq | samtools view -bh -F 2324 -q10 | samtools sort -O bam > align.bam
samtools index align.bam
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str nanozoo/nanopolish:0.13.2--9069b5c nanopolish index -d /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/ND33392.fq
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -w /home/wiktor/ont-str wkusmirek/f5c:1.4 /f5c/f5c eventalign -b align.bam -r /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/ND33392.fq -g /home/wiktor/ont-str/dataset/hd/chr4.fa --slow5 /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/reads.blow5 ---min-mapq 0 -o eventalign_reads_ND33392.tsv --min-recalib-events 5 --print-read-names --scale-events --samples

Estimate repeat counts:
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074177-3074197 --reference_file /home/wiktor/ont-str/dataset/hd/chr4_another_motifs_only_motifs.fa --kmer_model extern/kmer_models/legacy/legacy_r9.4_180mv_450bps_6mer/template_median68pA.model --kmer_length 6 --results /home/wiktor/ont-str-code/results-ND33392
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_NA12878.tsv --region chr4:3074177-3074197 --reference_file /home/wiktor/ont-str/dataset/hd/chr4_another_motifs_only_motifs.fa --kmer_model extern/kmer_models/legacy/legacy_r9.4_180mv_450bps_6mer/template_median68pA.model --kmer_length 6 --results /home/wiktor/ont-str-code/results-NA12878

With docker:
docker run --rm -it -v /home/wiktor/ont-str:/home/wiktor/ont-str -v /home/wiktor/ont-str-code:/home/wiktor/ont-str-code -w /home/wiktor/ont-str-code wkusmirek/ont-str-code python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/NA12878/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_NA12878.tsv --region chr4:3074177-3074197 --reference_file /home/wiktor/ont-str/dataset/hd/chr4_another_motifs_only_motifs.fa --kmer_model extern/kmer_models/legacy/legacy_r9.4_180mv_450bps_6mer/template_median68pA.model --results /home/wiktor/ont-str-code/results-NA12878

Plot times:
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074277-3074297 --results /home/wiktor/ont-str-code/results-ND33392-42
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074377-3074397 --results /home/wiktor/ont-str-code/results-ND33392-43
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074477-3074497 --results /home/wiktor/ont-str-code/results-ND33392-44
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074577-3074597 --results /home/wiktor/ont-str-code/results-ND33392-45
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074677-3074597 --results /home/wiktor/ont-str-code/results-ND33392-46
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074777-3074797 --results /home/wiktor/ont-str-code/results-ND33392-47
python3.11 src/main.py --fast5_dir /home/wiktor/ont-str/dataset/hd-deeprepeat/ND33392/workspace/pass/0 --f5c_eventalign_file /home/wiktor/ont-str/eventalign_reads_ND33392.tsv --region chr4:3074877-3074897 --results /home/wiktor/ont-str-code/results-ND33392-48


Wykrywanie wariantów:
grep 8fd7a488-d168-46fc-be90-45d31d34583b eventalign_reads_NA12878.tsv | grep -E -n 'TCCTTC|CAACAG'
grep 8fd7a488-d168-46fc-be90-45d31d34583b eventalign_reads_NA12878.tsv | sed -n '12870,13022p' | awk '{ print $7 }'  # wyciągnięcie eventów
grep 8fd7a488-d168-46fc-be90-45d31d34583b eventalign_reads_NA12878.tsv | sed -n '12870,13022p' | awk '{ print $14 }' # wyciągnięcie surowych prądów

grep be71ec5f-90bb-4d8d-a0bc-dfcf77a5e71b eventalign_reads_NA12878.tsv | grep -E -n 'TCCTTC|CAACAG'
grep be71ec5f-90bb-4d8d-a0bc-dfcf77a5e71b eventalign_reads_NA12878.tsv | sed -n '13252,13370p' | awk '{ print $7 }'  # wyciągnięcie eventów
grep be71ec5f-90bb-4d8d-a0bc-dfcf77a5e71b eventalign_reads_NA12878.tsv | sed -n '13252,13370p' | awk '{ print $14 }' # wyciągnięcie surowych prądów


