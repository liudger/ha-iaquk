FROM ghcr.io/home-assistant/home-assistant:dev

ENV DEVCONTAINER=true
ENV PREK_VERSION=0.3.11
ENV TY_VERSION=0.0.32
ENV UV_VERSION=0.11.8
ENV PATH="/root/.local/bin:${PATH}"

COPY ./container /container
COPY ./install /install

RUN \
    bash /install/init.sh \
    && bash /install/container.sh \
    && bash /install/cleanup.sh

CMD ["bash"]
