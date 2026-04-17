import yaml
import os

class Config:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
            
        self.data = self._config.get('data', {})
        self.etl = self._config.get('etl', {})
        self.ml = self._config.get('ml', {})
        
        # Override Databricks paths for local testing
        if self.data.get('raw_data_path', '').startswith('/dbfs'):
            self.data['raw_data_path'] = './data/raw'
        if self.data.get('processed_data_path', '').startswith('/dbfs'):
            self.data['processed_data_path'] = './data/processed'
