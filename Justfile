# depends on docker, 1password-cli, and jq
docker-build:
	docker build --build-arg "PIP_INDEX_URL=$(op item get 'Azure DevOps - Feed - Read PAT' --format=json | jq '.fields[] | select(.label=="url").value' -r)" -t harmonia:latest .
