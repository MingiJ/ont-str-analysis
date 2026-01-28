FROM nanozoo/guppy_cpu:5.0.7-1--47b84be
WORKDIR /opt

RUN apt-get update; \
    apt-get install -y git; \
    git clone https://github.com/fmfi-compbio/warpstr.git; \
    apt install -y software-properties-common; \
    apt-get install -y libbz2-dev

RUN apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget; \
    wget https://www.python.org/ftp/python/3.7.4/Python-3.7.4.tgz; \
    tar xzf Python-3.7.4.tgz; \
    cd Python-3.7.4; \
    ./configure; \
    make; \
    make install

WORKDIR /opt/warpstr

RUN sed -i 's/plot_summaries(locus.path, df_overview, caller_config.visualize_strand,//g' /opt/warpstr/src/caller/wrapper.py; \
    sed -i 's/caller_config.visualize_phase, caller_config.visualize_cost)//g' /opt/warpstr/src/caller/wrapper.py

ENV PIPENV_VENV_IN_PROJECT=1

RUN pip3.7 install pipenv; \
    pipenv sync --system
