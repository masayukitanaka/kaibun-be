
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

docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/b94f1e90-5e6b-4136-91fb-add3408b4eb0 .

docker push us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/b94f1e90-5e6b-4136-91fb-add3408b4eb0

gcloud run deploy kaibun-be-app \
  --image=us-central1-docker.pkg.dev/honolulu-467217/kaibun-repo/b94f1e90-5e6b-4136-91fb-add3408b4eb0 \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated 
