import json
import os
import time
from tkinter import messagebox
import urllib.request


def build_overlay_html():
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>APM Overlay</title>
  <style>
    html,body{width:100%;height:100%;margin:0;padding:0;background:transparent;}
    body{display:flex;align-items:center;justify-content:center;font-family:Inter,Segoe UI,Roboto,Consolas,monospace;}
    #apm{font-size:84px;font-weight:700;color:#e6eef6;text-shadow:0 2px 8px rgba(0,0,0,0.6)}
    #sub{position:absolute;bottom:8px;right:12px;font-size:14px;color:#9ca3af}
  </style>
</head>
<body>
  <div id=\"apm\">—</div>
  <div id=\"sub\">APM Overlay</div>
  <script>
    const urlBase = location.origin;
    function updateFromJson(j){
      const apm = Math.round(j.apm || 0);
      document.getElementById('apm').textContent = apm;
    }
    if (typeof(EventSource) !== 'undefined') {
      try{
        const es = new EventSource(urlBase + '/stream');
        es.onmessage = (e) => { try{ updateFromJson(JSON.parse(e.data)); }catch(_){} };
      }catch(err){
        setInterval(async ()=>{ try{ const res = await fetch(urlBase + '/stats'); if(res.ok){ updateFromJson(await res.json()); } }catch(_){} }, 250);
      }
    } else {
      setInterval(async ()=>{ try{ const res = await fetch(urlBase + '/stats'); if(res.ok){ updateFromJson(await res.json()); } }catch(_){} }, 250);
    }
  </script>
</body>
</html>"""
