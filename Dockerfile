FROM python:3.8

ADD dist/slackmgmt-0.1.0-py3-none-any.whl /slackmgmt-0.1.0-py3-none-any.whl
ADD config.toml /config.toml

RUN pip install /slackmgmt-0.1.0-py3-none-any.whl
CMD /usr/local/bin/python -m slackmgmt -d /config.toml
