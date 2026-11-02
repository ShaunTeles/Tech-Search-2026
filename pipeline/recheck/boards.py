import json,re,sys,time,html as H,requests
SP=sys.argv[1]
UA={"User-Agent":"Mozilla/5.0"}
T=re.compile(r"(product design|ux|ui[ /-]|ui designer|user experience|interaction design|design system|design engineer|ai designer|product designer)",re.I)
X=re.compile(r"(graphic|brand|motion|3d|web designer|writer|content designer|instructional|engineer(?!.*design)|developer|intern\b|junior|principal|director|vp )",re.I)
out=[]
# 4dayweek
for cat in ["design"]:
    p=1
    while p<=30:
        try:d=requests.get(f"https://4dayweek.io/api/jobs?category={cat}&page={p}",headers=UA,timeout=25).json()
        except Exception as e:print('4dw',p,e);break
        for j in d.get("jobs",[]):
            if T.search(j["title"]) and not X.search(j["title"]):
                out.append(dict(src="4dayweek",title=j["title"],company=j.get("company_name"),arr=j.get("work_arrangement"),loc=[(l.get("country"),l.get("continent"),l.get("work_arrangement")) for l in j.get("locations",[])],posted=j.get("posted"),url="https://4dayweek.io/remote-jobs/"+j["slug"],level=j.get("level"),salary=j.get("salary_min") or j.get("salary")))
        if not d.get("has_more"):break
        p+=1;time.sleep(.4)
print('4dw',len(out))
# WWR
for f in ["remote-design-jobs","remote-product-jobs"]:
    t=requests.get(f"https://weworkremotely.com/categories/{f}.rss",headers=UA,timeout=25).text
    for it in re.findall(r"<item>(.*?)</item>",t,re.S):
        g=lambda k:H.unescape((re.search(f"<{k}>(?:<!\\[CDATA\\[)?(.*?)(?:\\]\\]>)?</{k}>",it,re.S) or [0,""])[1])
        ti=g("title")
        if T.search(ti) and not X.search(ti):
            c,_,r=ti.partition(":");out.append(dict(src="wwr",title=r.strip(),company=c.strip(),arr="remote",loc=g("region"),posted=g("pubDate"),url=g("link")))
print('wwr',len(out))
# Working Nomads
for j in requests.get("https://www.workingnomads.com/api/exposed_jobs/",headers=UA,timeout=25).json():
    if T.search(j["title"]) and not X.search(j["title"]):out.append(dict(src="wn",title=j["title"],company=j.get("company_name"),arr="remote",loc=j.get("location"),posted=j.get("pub_date"),url=j.get("url")))
print('wn',len(out))
# Himalayas
off=0
while off<3000:
    try:d=requests.get(f"https://himalayas.app/jobs/api?limit=20&offset={off}",headers=UA,timeout=25).json()
    except Exception as e:print('him',off,e);break
    js=d.get("jobs",[])
    if not js:break
    for j in js:
        if T.search(j["title"]) and not X.search(j["title"]):out.append(dict(src="himalayas",title=j["title"],company=j.get("companyName"),arr="remote",loc=j.get("locationRestrictions"),tz=j.get("timezoneRestrictions"),posted=j.get("pubDate"),url=j.get("applicationLink") or j.get("guid"),salary=[j.get("minSalary"),j.get("maxSalary"),j.get("currency")],level=j.get("seniority")))
    off+=20;time.sleep(.25)
print('him',len(out))
# Direct ATS: remote-first, Europe-friendly
B={"ashby":"supabase resend linear notion ramp posthog vercel cursor anysphere replit perplexity elevenlabs synthesia n8n lovable langchain sierra clay zapier deel oyster revolut wise pleo mistral dust photoroom attio granola raycast incident browserbase runway modal retool hex sanity neon tines kit stytch lindy gamma pitch deepl legora tldraw fal rilla poolside helsing parloa black-forest-labs".split(),
"greenhouse":"remotecom gitlab automattic hotjar contentsquare intercom figma datadog mongodb stripe cloudflare airtable webflow doist grafanalabs canonical metabase discord duolingo elastic twilio toptal bitpanda n26 monzo getyourguide adyen sumup taxfix trivago hubspot algolia typeform gorgias dynatrace".split(),
"lever":"mistral spotify palantir whoop binance kraken wikimedia dashlane aircall qonto".split(),
"workable":"fluxon kickstarter pitch hospitable".split()}
sys.path.insert(0,SP)
GH=lambda s:requests.get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true",timeout=20)
def add(company,title,loc,url,upd,**k):
    if T.search(title) and not X.search(title):out.append(dict(src="ats",title=title,company=company,loc=loc,posted=upd,url=url,**k))
for s in B["ashby"]:
    try:
        r=requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{s}",timeout=20)
        if r.ok:
            for j in r.json().get("jobs",[]):add(s,j["title"],j.get("location"),j.get("jobUrl"),j.get("publishedAt"),remote=j.get("isRemote"),workplace=j.get("workplaceType"),arr="remote" if j.get("isRemote") else j.get("workplaceType"))
    except Exception:pass
for s in B["greenhouse"]:
    try:
        r=requests.get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs",timeout=20)
        if r.ok:
            for j in r.json().get("jobs",[]):add(s,j["title"],(j.get("location") or {}).get("name"),j["absolute_url"],j.get("updated_at"))
    except Exception:pass
for s in B["lever"]:
    for host in("api.lever.co","api.eu.lever.co"):
        try:
            r=requests.get(f"https://{host}/v0/postings/{s}?mode=json",timeout=20)
            if r.ok:
                for j in r.json():add(s,j["text"],(j.get("categories") or {}).get("location"),j["hostedUrl"],j.get("createdAt"),workplace=j.get("workplaceType"))
                break
        except Exception:pass
for s in B["workable"]:
    try:
        r=requests.get(f"https://apply.workable.com/api/v1/widget/accounts/{s}",timeout=20)
        if r.ok:
            for j in r.json().get("jobs",[]):add(s,j["title"],f"{j.get('city')},{j.get('country')}",j.get("url"),j.get("published_on"),remote=j.get("telecommuting"))
    except Exception:pass
print('ats',len(out))
json.dump(out,open(f"{SP}/boards.json","w"),ensure_ascii=False,indent=0)
print("DONE",len(out))
