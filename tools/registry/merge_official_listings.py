"""Offline addition of reviewed listing identities to the standalone backend registry.

Never imports the old monorepo builder or fetches providers. Input must be the
existing saved registry and the checked-in reviewed identity-only source.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.registry.official_listings import merge_official_listings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Explicit output file; inputs are never overwritten implicitly')
    args=parser.parse_args()
    registry=json.loads((ROOT/'data/registry.json').read_text())
    source=json.loads((ROOT/'data/official-listings-ngx.json').read_text())
    result=merge_official_listings(registry,source)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
if __name__=='__main__':main()
