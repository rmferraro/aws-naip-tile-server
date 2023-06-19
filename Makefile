build-UtilsLambdaLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python/aws_naip_tile_server"
	cp -r aws_naip_tile_server/layers "$(ARTIFACTS_DIR)/python/aws_naip_tile_server"
	cp -r aws_naip_tile_server/data "$(ARTIFACTS_DIR)/python/aws_naip_tile_server"
	poetry export --without-hashes > "$(ARTIFACTS_DIR)/python/requirements.txt"
	python -m pip install -r "$(ARTIFACTS_DIR)/python/requirements.txt" -t "$(ARTIFACTS_DIR)/python"
	rm "$(ARTIFACTS_DIR)/python/requirements.txt"
