
## コンテナローカル実行

docker build -t kaibun-be .

docker run -d -p 8080:8080 --name kaibun-be-container kaibun-be


## プロジェクト設定（初回のみ）

gcloud config set project honolulu-467217

gcloud artifacts repositories create kaibun-repo \
  --repository-format=docker \
  --location=us-central1

gcloud auth configure-docker us-central1-docker.pkg.dev


## イメージのビルド/push

export COMMIT_HASH=6975738341d2c313ae61a4a4580a3a85fcdc9c73

docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/$COMMIT_HASH .

docker push us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/$COMMIT_HASH

gcloud run deploy kaibun-be-app \
  --image=us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/$COMMIT_HASH \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated 
