import logging.config
import logging
import json
import os


def setup(job_path):
    with open(os.path.join(job_path, 'config.json'), 'r') as f:
        cfg = json.load(f)['logging']
        try:
            # Try to path filename's to point out to job folder
            for h in cfg['handlers'].values():
                if 'filename' in h:
                    p = os.path.join(job_path, h['filename'])
                    h['filename'] = p
        except: pass
        logging.config.dictConfig(cfg)

def logger():
    return logging.getLogger('root')
