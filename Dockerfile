FROM python:3.11
WORKDIR /usr/local/app

RUN pip install --upgrade --no-cache-dir --force-reinstall dtaidistance
RUN pip install pandas Bio matplotlib
RUN pip install scipy ont_fast5_api seaborn

# Install the application dependencies
COPY src ./
