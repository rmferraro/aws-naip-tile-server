build-UtilsLambdaLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python/src"
	cp -r src/utils "$(ARTIFACTS_DIR)/python/src"
	cp -r src/data "$(ARTIFACTS_DIR)/python/src"
	poetry export --without-hashes > "$(ARTIFACTS_DIR)/python/requirements.txt"
	python -m pip install -r "$(ARTIFACTS_DIR)/python/requirements.txt" -t "$(ARTIFACTS_DIR)/python"
	rm "$(ARTIFACTS_DIR)/python/requirements.txt"
