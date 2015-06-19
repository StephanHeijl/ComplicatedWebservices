# -*- coding: utf-8 -*-
import json
import time
from collections import OrderedDict
import requests
import dicttoxml
import xmltodict
from Bio.Blast import NCBIWWW

from flask import Flask, Response, url_for
from flask.ext.cache import Cache

cache = Cache(config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': '/home/stephan/ComplicatedWebservices', 'CACHE_DEFAULT_TIMEOUT':60*60*24*30})
app = Flask(__name__)
cache.init_app(app)

@app.route('/')
def hai_gais():
    """This is the index page."""

    text = u"""
<html>
<head><title>Complicated Web Services</title></head>
<body style="font-family: monospace;">
<pre>
.--.   .--.    ___    _    .-'''-.      .-./`)     .-''-.     .-'''-.                     .-'''-.    
|  | _/  /   .'   |  | |  / _     \     \ '_ .') .'_ _   \   / _     \           _.--``) /   _   \   
| (`' ) /    |   .'  | | (`' )/`--'    (_ (_) _)/ ( ` )   ' (`' )/`--'          /_ _.-` |__/` '.  |  
|(_ ()_)     .'  '_  | |(_ o _).         / .  \. (_ o _)  |(_ o _).            /( ' )      .--'  /   
| (_,_)   __ '   ( \.-.| (_,_). '.  ___  |-'`| |  (_,_)___| (_,_). '.         ((_{;}_)  ___'--._ _\  
|  |\ \  |  |' (`. _` /|.---.  \  :|   | |   ' '  \   .---..---.  \  :         \(_,_)  |   |  ( ` )  
|  | \ `'   /| (_ (_) _)\    `-'  ||   `-'  /   \  `-'    /\    `-'  |          \   `-.|   `-(_{;}_) 
|  |  \    /  \ /  . \ / \       /  \      /     \       /  \       /            `---._)\     (_,_)  
`--'   `'-'    ``-'`-''   `-...-'    `-..-'       `'-..-'    `-...-'                     `-..__.-'   
                                                                                                     
.▄▄ · ▄▄▄▄▄▄▄▄ . ▄▄▄· ▄ .▄ ▄▄▄·  ▐ ▄      ▐▄▄▄      ▄▄▄  ▪  .▄▄ ·          ▐▄▄▄ ▄▄▄· ▄▄▄   ▐ ▄       
▐█ ▀. •██  ▀▄.▀·▐█ ▄███▪▐█▐█ ▀█ •█▌▐█      ·██▪     ▀▄ █·██ ▐█ ▀.           ·██▐█ ▀█ ▀▄ █·•█▌▐█▪     
▄▀▀▀█▄ ▐█.▪▐▀▀▪▄ ██▀·██▀▐█▄█▀▀█ ▐█▐▐▌    ▪▄ ██ ▄█▀▄ ▐▀▀▄ ▐█·▄▀▀▀█▄        ▪▄ ██▄█▀▀█ ▐▀▀▄ ▐█▐▐▌ ▄█▀▄ 
▐█▄▪▐█ ▐█▌·▐█▄▄▌▐█▪·•██▌▐▀▐█ ▪▐▌██▐█▌    ▐▌▐█▌▐█▌.▐▌▐█•█▌▐█▌▐█▄▪▐█        ▐▌▐█▌▐█ ▪▐▌▐█•█▌██▐█▌▐█▌.▐▌
 ▀▀▀▀  ▀▀▀  ▀▀▀ .▀   ▀▀▀ · ▀  ▀ ▀▀ █▪     ▀▀▀• ▀█▄▀▪.▀  ▀▀▀▀ ▀▀▀▀          ▀▀▀• ▀  ▀ .▀  ▀▀▀ █▪ ▀█▄▀▪                                                                                                                                                                
</pre>

Currently available services:
<ul style="list-style-type:square;">
%s
</ul>
</body>
</html>
""" 
    rules = ""
    for rule in app.url_map.iter_rules():
        try:
            rules+="<li><b>%s</b> - <u>%s</u>, %s</li>\n" % (rule.endpoint, str(rule), eval(rule.endpoint).__doc__.replace("\n","<br/>"))
        except:
            continue
    return text % rules

def has_no_empty_params(rule):
    return True
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def to_dict(input_ordered_dict):
    return json.loads(json.dumps(input_ordered_dict))

@app.route('/uniprot/<name>')
def getUniprotInfo(name):
    """Get an XML formatted index of all Uniprot results for the given query.  """
    uniprotSearchUrl = "http://www.uniprot.org/uniprot/?format=json&limit=1&query=\"" + name.replace("_"," ") + "\""
    r = requests.get(uniprotSearchUrl)
    results = []
    for result in r.json():
        detailedResults = requests.get("http://www.uniprot.org/uniprot/%s.xml" % result["id"])
        loadedDetails = to_dict(xmltodict.parse(detailedResults.content))
        result["sequence"] = loadedDetails["uniprot"]["entry"]["sequence"]["#text"].replace("\n","")
        result["ids"] = {}
        for ref in loadedDetails["uniprot"]["entry"]["dbReference"]:
            try:
                result["ids"][ref["@type"]] = ref["@id"]
            except KeyError:
               continue
	results.append(result)
    return Response( dicttoxml.dicttoxml(results), mimetype="text/xml")

@app.route('/pubmed/<name>')
@cache.cached()
def getPubmedInfo(name):
    """ Get an XML formatted list of Pubmed articles matching the query, 
	including all available data for each article."""
    pubmedUrl = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=" + name
    pubmedDownloadUrl = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id="
    r = requests.get(pubmedUrl)
    rdict = to_dict(xmltodict.parse(r.content))["eSearchResult"]["IdList"]
    try:
        ids = ",".join(rdict.values())
    except TypeError:
        ids = ",".join(rdict.values()[0])
    except AttributeError:
        return "<none></none>"

    return Response(requests.get(pubmedDownloadUrl+ids).content, mimetype="text/xml")
    

@app.route('/go/<goid>')
def getGOInfo(goid,dryrun=False):
    """ Get XML formatted GO information for a given GO ID. """
    goUrl = "http://www.ebi.ac.uk/QuickGO/GTerm?id=%s&format=oboxml" % goid
    r = requests.get(goUrl) 
    return Response( r.content, mimetype="text/xml" )

@app.route('/pfam/<pfamid>')
def getPFAMinfo(pfamid):
    """ Get XML formatted PFAM information for a given PFAM ID. """
    pfamUrl = "http://pfam.xfam.org/family/%s/?output=xml" % pfamid
    r = requests.get(pfamUrl)
    return Response( r.content, mimetype="text/xml" )

@app.route('/blast/<AAsequence>')
@app.route('/blast/<AAsequence>/<dryrun>')
def getBLAST(AAsequence,dryrun=False):
    """ Accepts an amino acid sequence and BLASTs it with the NCBI QBlast service. 
        Add /dryrun to the end of the URL to perform a dry run. """
    if dryrun == "dryrun":
        with open("output.xml") as output:
            return Response( output.read(), mimetype="text/xml" )
    AAsequence = "".join([c for c in AAsequence if ord(c) in range(65,91) or ord(c) in range(97,123)])
    result_handle = NCBIWWW.qblast("blastp","nr", AAsequence)
    return result_handle.read()

@app.route('/jarno/')
def jarno():
    """ Returns "Jarno". """
    return "Jarno"

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8000,debug=True,threaded=True)
