FROM python:3.10-bullseye
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install FlagEmbedding Flask gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . /app
WORKDIR /app
RUN pip install -r ./requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
EXPOSE 8000
CMD [ "python", "-m", "gunicorn", "app:app" , "-b", ":8000"]