FROM docker.io/datopian/giftless:0.5.0
MAINTAINER "Adam Thornton <athornton@lsst.org>"

ARG  USER_NAME giftless
USER root

RUN  DEBIAN_FRONTEND=noninteractive apt-get update && \
       apt-get install -y git make

# First, rebuild the image.  The pypi tag is very stale
ARG  SW=/opt/lsst/software
ARG  V="0.5.1dev0"

RUN  mkdir -p $SW && \
      pip uninstall -y giftless && \
      rm -rf /app
RUN  git clone https://github.com/datopian/giftless /app && \
      echo $V > /app/VERSION
RUN  cd /app && \
     make requirements.txt && \
     pip install --upgrade --force-reinstall /app
# Force flask/werkzeug -- don't know why requirements.txt doesn't.
RUN  pip uninstall -y werkzeug flask flask-classful && \
     pip install --force-reinstall --no-dependencies \
     'werkzeug==2.1.1' 'flask==2.1.3' 'flask-classful==0.15.0b1'

# Add Rubin GitHub proxy authenticator
ARG  GPA=/opt/lsst/software/giftless-github-proxy-auth
COPY . $GPA
RUN  pip install PyGitHub
RUN  pip install $GPA
