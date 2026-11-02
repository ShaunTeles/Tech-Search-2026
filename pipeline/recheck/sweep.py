import re,requests,html as H
from concurrent.futures import ThreadPoolExecutor as T
UA={"User-Agent":"Mozilla/5.0"}
A="""sanity contentful storyblok miro pitch tally typefully cal calcom plane appflowy huggingface weights-biases wandb stability doppler mollie paddle lemon-squeezy lemonsqueezy loom superhuman framer spline rive penpot maze dovetail usermaven pendo userpilot appcues chameleon mixpanel amplitude heap fullstory segment customerio klaviyo brevo sendinblue mailchimp omnisend gorgias shopify vinted bolt glovo wolt getir flink picnic oda hellofresh gousto mindvalley preply babbel busuu blinkist headspace flo flo-health bending-spoons paired tide wise bunq trade-republic scalable-capital pleo spendesk payhawk ageras holded factorial personio remote deel oyster-hr lano rippling hibob workable teamwork toggl hubstaff doist buffer convertkit kit ghost beehiiv substack automattic wordpress elementor wix hostinger semrush similarweb ahrefs productboard mews kiwi kiwicom eset socialbakers emplifi smartlook gooddata apify make integromat zapier tines workato bardeen relevanceai relevance-ai cognigy poly-ai polyai aleph-alpha deepset nabla tome beautiful-ai decktopus jasper writer copy-ai descript veed captions opus heygen d-id tavus pika luma suno lightricks ideogram leonardo krea freepik canva envato visme piktochart""".split()
D=re.compile(r"product design|ux |ux/|ui/|ui design|user experience",re.I);X=re.compile(r"junior|intern|graduate|manager|director|head of|research|writer|engineer|principal|benelux",re.I)
RM=re.compile(r"remote|anywhere|europe|emea|czech|prague|praha|global|worldwide",re.I)
def chk(s):
    o=[]
    try:
        r=requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{s}",timeout=15)
        if r.ok:
            for j in r.json().get("jobs",[]):
                if D.search(j["title"]) and not X.search(j["title"]):o.append(("ash",s,j["title"],j.get("location"),[x["location"] for x in j.get("secondaryLocations",[])][:6],j.get("workplaceType"),j.get("publishedAt","")[:10],j["jobUrl"]))
    except Exception:pass
    try:
        r=requests.get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs",timeout=15)
        if r.ok:
            for j in r.json().get("jobs",[]):
                if D.search(j["title"]) and not X.search(j["title"]):o.append(("gh",s,j["title"],j["location"]["name"],"",j.get("first_published","")[:10],j["absolute_url"]))
    except Exception:pass
    for h in("api.lever.co","api.eu.lever.co"):
        try:
            r=requests.get(f"https://{h}/v0/postings/{s}?mode=json",timeout=15)
            if r.ok:
                for j in r.json():
                    if D.search(j["text"]) and not X.search(j["text"]):o.append(("lev",s,j["text"],j["categories"].get("location"),j.get("workplaceType"),"",j["hostedUrl"]))
                break
        except Exception:pass
    try:
        r=requests.get(f"https://apply.workable.com/api/v1/widget/accounts/{s}",timeout=15)
        if r.ok:
            for j in r.json().get("jobs",[]):
                if D.search(j["title"]) and not X.search(j["title"]):o.append(("wk",s,j["title"],j.get("country"),j.get("telecommuting"),j.get("published_on"),j.get("url")))
    except Exception:pass
    return o
seen=set()
with T(25) as e:
    for rs in e.map(chk,sorted(set(A))):
        for x in rs:
            if x[-1] in seen:continue
            seen.add(x[-1]);l=" ".join(str(y) for y in x[3:6])
            if RM.search(l):print(x)
