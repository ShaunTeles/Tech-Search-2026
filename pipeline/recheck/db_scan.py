import json,re,sys,threading,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urljoin,urlparse
import requests,html as H
SP=sys.argv[1];SRC=sys.argv[2]
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
ROLE=re.compile(r"(product design|ux|ui[ /-]|ui designer|user experience|user research|interaction design|design system|design engineer|service designer|product manager|product owner|head of product|head of design|design lead|produktov\w+ design)",re.I)
CAREER=re.compile(r"(career|jobs|kariera|kariéra|join|hiring|volna-mista|volná místa|work-with-us|pracovni|open-positions|prace-u-nas)",re.I)
ATS=[("greenhouse",r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board/js\?for=)?([a-z0-9_-]+)"),("lever",r"jobs(?:\.eu)?\.lever\.co/([a-z0-9_.-]+)"),("ashby",r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"),("workable",r"apply\.workable\.com/([a-z0-9_-]+)"),("smartrecruiters",r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),("teamtailor",r"https?://([a-z0-9-]+)\.teamtailor\.com"),("recruitee",r"https?://([a-z0-9-]+)\.recruitee\.com"),("personio",r"https?://([a-z0-9-]+)\.jobs\.personio\.(?:de|com)")]
BAD={"embed","js","jobs","careers","www","app","api","static","assets","cdn"}
def get(u,t=10):
    try:return requests.get(u,headers=UA,timeout=t,allow_redirects=True)
    except Exception:return None
def strip(s):return H.unescape(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s))).strip()
def ats_jobs(k,s):
    o=[]
    try:
        if k=="greenhouse":
            r=get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")
            if r is not None and r.status_code==200:o=[dict(title=j["title"],location=(j.get("location") or {}).get("name",""),url=j["absolute_url"],updated=j.get("updated_at","")) for j in r.json().get("jobs",[])]
        elif k=="lever":
            r=get(f"https://api.lever.co/v0/postings/{s}?mode=json")
            if r is not None and r.status_code!=200:r=get(f"https://api.eu.lever.co/v0/postings/{s}?mode=json")
            if r is not None and r.status_code==200:o=[dict(title=j["text"],location=(j.get("categories") or {}).get("location",""),url=j["hostedUrl"],updated=j.get("createdAt",""),workplace=j.get("workplaceType","")) for j in r.json()]
        elif k=="ashby":
            r=get(f"https://api.ashbyhq.com/posting-api/job-board/{s}")
            if r is not None and r.status_code==200:o=[dict(title=j["title"],location=j.get("location",""),url=j.get("jobUrl",""),updated=j.get("publishedAt",""),workplace=j.get("workplaceType",""),remote=j.get("isRemote")) for j in r.json().get("jobs",[]) if j.get("isListed",True)]
        elif k=="workable":
            r=get(f"https://apply.workable.com/api/v1/widget/accounts/{s}?details=false")
            if r is not None and r.status_code==200:o=[dict(title=j["title"],location=", ".join(x for x in [j.get("city"),j.get("country")] if x),url=j.get("url",""),updated=j.get("published_on",""),remote=j.get("telecommuting")) for j in r.json().get("jobs",[])]
        elif k=="smartrecruiters":
            r=get(f"https://api.smartrecruiters.com/v1/companies/{s}/postings")
            if r is not None and r.status_code==200:o=[dict(title=j["name"],location=(j.get("location") or {}).get("fullLocation",""),url=f"https://jobs.smartrecruiters.com/{s}/{j['id']}",updated=j.get("releasedDate",""),remote=(j.get("location") or {}).get("remote")) for j in r.json().get("content",[])]
        elif k=="recruitee":
            r=get(f"https://{s}.recruitee.com/api/offers/")
            if r is not None and r.status_code==200:o=[dict(title=j["title"],location=j.get("location",""),url=j.get("careers_url",""),updated=j.get("published_at",""),remote=j.get("remote")) for j in r.json().get("offers",[])]
        elif k=="teamtailor":
            r=get(f"https://{s}.teamtailor.com/jobs")
            if r is not None and r.status_code==200:
                for m in re.finditer(r'<a[^>]+href="(https://[^"]+/jobs/\d+[^"]*)"[^>]*>(.*?)</a>',r.text,re.S):o.append(dict(title=strip(m[2])[:120],location="",url=m[1],updated=""))
        elif k=="personio":
            r=get(f"https://{s}.jobs.personio.de/xml")
            if r is not None and r.status_code==200:
                for m in re.finditer(r"<position>(.*?)</position>",r.text,re.S):
                    g=lambda t:(re.search(f"<{t}>(.*?)</{t}>",m[1],re.S) or [0,""])[1]
                    o.append(dict(title=H.unescape(g("name")),location=g("office"),url=f"https://{s}.jobs.personio.de/job/{g('id')}",updated=g("createdAt")))
    except Exception:pass
    return o
def scan(rec):
    w=(rec.get("website") or "").strip();res=dict(name=rec["name"],website=w,source=rec.get("source",""),old=bool(int(rec.get("product_jobs") or 0) or int(rec.get("design_jobs") or 0) or int(rec.get("ux_jobs") or 0)),method=rec.get("job_check_method",""),status="",jobs=[],ats=[],career_url="",total=0)
    base=w if w.startswith("http") else "https://"+w
    r=get(base)
    if r is None or r.status_code>=400:
        r2=get(base.replace("https://","http://"))
        if r2 is None or r2.status_code>=400:res["status"]="site_down";r=None
        else:r=r2
    pages=[];found=set();host=urlparse(base).netloc.replace("www.","")
    if r is not None:
        res["status"]="ok";pages.append((r.url,r.text))
        links=[urljoin(r.url,m) for m in re.findall(r'href=["\']([^"\'#]+)',r.text)]
        c=[l for l in links if CAREER.search(l) and not re.search(r"\.(css|js|png|jpg|svg|pdf)($|\?)",l) and "linkedin" not in l and "facebook" not in l]
        c=sorted(set(c),key=len)[:2]
        if not c:c=[r.url.rstrip("/")+p for p in("/careers","/jobs","/kariera")]
        for u in c:
            x=get(u,8)
            if x is not None and x.status_code==200 and len(x.text)>500:
                pages.append((x.url,x.text))
                if not res["career_url"]:res["career_url"]=x.url
    for pu,t in pages:
        for k,p in ATS:
            for s in re.findall(p,t+" "+pu):
                if s.lower() not in BAD:found.add((k,s))
    stem=host.split(":")[0].split(".")[0]
    if stem and len(stem)>2:
        for k in("greenhouse","lever","ashby"):found.add((k,stem))
    seen=set()
    for k,s in found:
        js=ats_jobs(k,s)
        if js:
            res["ats"].append(f"{k}:{s}");res["total"]+=len(js)
            for j in js:
                if ROLE.search(j["title"]) and j["url"] not in seen:
                    seen.add(j["url"]);j["via"]=k;res["jobs"].append(j)
    if not res["ats"]:
        for pu,t in pages[1:]:
            for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',t,re.S):
                tx=strip(m[2])
                if 4<len(tx)<110 and ROLE.search(tx):
                    u=urljoin(pu,m[1])
                    if u not in seen:
                        seen.add(u);res["jobs"].append(dict(title=tx,location="",url=u,updated="",via="careers_page"))
    return res
recs=[r for r in json.load(open(SRC)) if (r.get("website") or "").strip()]
print(len(recs),flush=True)
out=open(f"{SP}/db_scan.jsonl","w");lock=threading.Lock();n=0
with ThreadPoolExecutor(40) as ex:
    for f in as_completed([ex.submit(scan,r) for r in recs]):
        try:x=f.result()
        except Exception as e:continue
        with lock:
            out.write(json.dumps(x,ensure_ascii=False)+"\n");out.flush();n+=1
            if n%250==0:print(n,flush=True)
print("DONE",n,flush=True)
