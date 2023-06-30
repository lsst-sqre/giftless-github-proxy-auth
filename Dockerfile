FROM docker.io/datopian/giftless:0.5.0
MAINTAINER "Adam Thornton <athornton@lsst.org>"

ARG  USER_NAME giftless
USER root

RUN  DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y git

# Add Rubin GitHub proxy authenticator
ARG  GPA=/opt/lsst/software/giftless-github-proxy-auth
COPY . $GPA
RUN  pip install PyGitHub  # We already have giftless
RUN  pip install $GPA
