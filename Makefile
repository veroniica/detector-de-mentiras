.PHONY: dev test lint deploy clean

# Development setup
dev:
	pip install -r requirements.txt --user
	pip install pytest pytest-cov pylint --user

# Run tests
test:
	python -m pytest tests/ -v

# Run linting
lint:
	python -m pylint src/

# Build and deploy
deploy:
	mkdir -p dist
	cd src/lambda && zip -r ../../dist/audio_processor.zip audio_processor.py
	cd src/lambda && zip -r ../../dist/transcription.zip transcription.py
	cd src/lambda && zip -r ../../dist/sentiment_analysis.zip sentiment_analysis.py
	cd src/lambda && zip -r ../../dist/summary_generator.zip summary_generator.py
	cd src/lambda && zip -r ../../dist/inconsistency_detector.zip inconsistency_detector.py
	aws s3 cp dist/ s3://$(RESULTS_BUCKET)/lambda/ --recursive
	aws cloudformation deploy --template-file template/template.yaml --stack-name forensic-audio-analysis --capabilities CAPABILITY_IAM

# Clean build artifacts
clean:
	rm -rf dist/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete