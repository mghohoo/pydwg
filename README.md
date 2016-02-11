# Pydwg & Pydwg-tools

*This is just an initial version.*
*In this version, there are some issues relating to the memory management.*

A DWG file format parser and a tool set for digital forensics and incident response.


## Quick start

Clone the git repo `https://github.com/sarahchung/pydwg.git` or [download it](https://github.com/sarahchung/pydwg/zipball/master)

Execute `pydwg-tools` to analyze an DWG file
<pre>
python  pydwg-tools.py  -h
</pre>

Examples of usage
<pre>
python  pydwg-tools.py  v  sample-r21.dwg
python  pydwg-tools.py  m  sample-r18.dwg
</pre>


## Key Features

#### Target
* AutoCAD DWG R18 and R21 file
* AutoCAD DWG R24 and R27 file (todo)

#### Features of *pydwg-tools*
* Format validation (argument 'v')

* Metadata extraction (argument 'm')

* Handle distribution analysis (argument 'h')


## License

MIT License


## Feedback

Please submit feedback via the pydwg [tracker](http://github.com/sarahchung/pydwg/issues)

Author: Hyunji Chung (localchung@gmail.com)

[![Analytics](https://ga-beacon.appspot.com/UA-45447336-2/pydwg/readme?pixel)](https://github.com/igrigorik/ga-beacon)


