"""Explicitly download public source files and verify their declared licenses/hashes."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,required=True);args=parser.parse_args();args.destination.mkdir(parents=True,exist_ok=True)
for article in (7765196,7765310,7770599,7770422):
    with urllib.request.urlopen('https://api.figshare.com/v2/articles/'+str(article),timeout=60) as response: metadata=json.load(response)
    if metadata['license']['name']!='CC BY 4.0': raise RuntimeError('Unexpected source license; download stopped')
    (args.destination/(str(article)+'-metadata.json')).write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    for record in metadata['files']:
        name=record['name']
        if Path(name).name!=name: raise RuntimeError('Unexpected source filename')
        path=args.destination/name
        if not path.exists():
            with urllib.request.urlopen(record['download_url'],timeout=60) as response,path.open('wb') as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
        expected=record.get('computed_md5') or record.get('supplied_md5')
        if not expected or hashlib.md5(path.read_bytes()).hexdigest()!=expected: raise RuntimeError('Source checksum mismatch')
        print(name,'verified')
