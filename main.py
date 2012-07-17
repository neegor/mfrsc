# -*- coding: utf-8 -*-

import webapp2 as webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import lxml.html
from google.appengine.api import memcache
from setting import jinja_environment
from math import sqrt

from google.appengine.api import urlfetch

class MainPage(webapp.RequestHandler):
    def get(self):
        template_values = {}
        template = jinja_environment.get_template("index.html")
        self.response.out.write(template.render(template_values))

class Facebook(webapp.RequestHandler):
    def post(self): 
        pass
    def get_total_count(self, listUrl):
        lists = {}
        url = "http://api.facebook.com/restserver.php?method=links.getStats&urls=" + listUrl
        
        result = urlfetch.fetch(url=url,headers={'use_intranet': 'yes'})
        if result.status_code == 200:
            doc = lxml.html.document_fromstring(result.content)

            for item in doc.cssselect('link_stat'):
                total_count = item.cssselect('total_count')[0].text_content()
                url = item.cssselect('url')[0].text_content()
                lists.update({unicode(url):total_count})
                
        return lists
    
class Segregation(webapp.RequestHandler):
    def get_segregation(self, fb, bing):
        if fb==0: 
            return -bing
        else:
            z = 1.64485
            n=fb+bing
            phat=1.0*fb/n
            rating = (phat+z*z/(2*n)-z*sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n)
            return rating
            
    
    def post(self): 
        pass
        
class Bing(Segregation, Facebook, webapp.RequestHandler):
    def post(self):
        s = self.request.get("search")
        data = memcache.get(s)
        if data is not None:
            sorted_dict = data
        else:
            listRes = []
            lists = {}
            listLI = []
            listUrl = ""
            resultList = {}
            for i in ["1", "11", "21", "31", "41"]:
                url = u"http://www.bing.com/search?q=" + s + "&first=" + i
                
                result = urlfetch.fetch(url=url,headers={'use_intranet': 'yes'})
                if result.status_code == 200:
                    doc = lxml.html.document_fromstring(result.content)

                    for ul in doc.cssselect('ul.sb_results'):
                        for li in ul.cssselect('li.sa_wr'):
                            url = li.cssselect('cite')[0].text_content()
                            listUrl += u"," + unicode(url.split(",")[0])
                            #if len(listUrl)
                            listLI.append(li)  
                        lists.update(self.get_total_count(listUrl))
                        listUrl = ""
            
            bing = 0
            for li in listLI:
                bing += 1
                discription = li.cssselect('p')[0].text_content() if len(li.cssselect('p')) >= 1 else ""
                title = li.cssselect('a')[0].text_content()
                url = li.cssselect('a')[0].get('href')
                cite = li.cssselect('cite')[0].text_content() 
                likes = (lists[unicode(cite)]) if lists.has_key(unicode(cite)) else 0
                ratio = self.get_segregation(float(likes), float(bing))
                resultList.update({"url":url, "discription":unicode(discription), "title":title, "cite":unicode(cite), "likes":likes, "ratio":ratio})
                listRes.append(resultList)
                resultList = {}
                
            sorted_dict = (sorted(listRes, key=lambda x:x["ratio"], reverse=True))[0:15]
            memcache.add(s, sorted_dict, 60 * 60 * 24)
        
        
        template = jinja_environment.get_template("result.html")
        self.response.out.write(template.render({"results":sorted_dict}))
 
    def get(self):
        self.post()

app = webapp.WSGIApplication([('/', MainPage),
                              ('/find', Bing)], debug=True)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
