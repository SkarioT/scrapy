import scrapy
import lxml.html
from github.items import GithubItem
""""
Test proj for studyng Scrapy
"""
class GitHubSpider(scrapy.Spider):
    name = "GitHub"
    start_urls = ['https://github.com/SkarioT','https://github.com/asdasdasdafadsb','https://github.com/scrapy']
    start_urls = ['https://github.com/scrapy','https://github.com/SkarioT']
    
    
    def parse(self, response):
        org_resp_url = response.css('li[data-tab-item="org-header-repositories-tab"] a::attr("href")').get()
        if org_resp_url == None:
            user_resp_url = response.css('nav.UnderlineNav-body a::attr("href")')[1].get()
            yield response.follow(user_resp_url,callback=self.parse_user_repos_list)
        else:
            yield response.follow(org_resp_url,callback=self.parse_org_repos_list)
        
        
    #for parse user repos list
    def parse_user_repos_list(self, response):
        for repos in response.css('div[id="user-repositories-list"] ul li'):
            repos_url = repos.css('h3.wb-break-all a::attr("href")').get()
            yield response.follow(repos_url,callback=self.parse_user_repos_info)
            
    #for parse org repos list
    def parse_org_repos_list(self, response):
        org_rep_list = response.css('div[class="org-repos repo-list"] ul li')
        for repos in org_rep_list:
            repos_url = repos.css('h3.wb-break-all a::attr("href")').get()
            yield response.follow(repos_url,callback=self.parse_user_repos_info)
    
    # for parse ORG & USER repos
    def parse_user_repos_info(self,response):
        repos_name = response.css('strong[itemprop="name"] a::text').get()
        repos_url = response.url#response.css('div.BorderGrid-cell div[class="my-3 d-flex flex-items-center"] span a::attr("href")').get()
        repos_about = response.css('div.BorderGrid-cell div[class="f4 my-3 color-fg-muted text-italic"]::text').get()
        repos_url_from_about = None
        if repos_about == None: #для своих проектов которые форки чужих ОРГ проектов
            #иногда в описании присутствуют ссылки, получаю их
            repos_about_link = response.css('div.BorderGrid-cell p[class="f4 my-3"] a::text').get()
            repos_url_from_about = repos_about_link # закиываю эту ссылку во временную переменную
            if repos_about_link == None:
                #если ссылки нет - делаю пустую строку
                repos_about_link = ""
            # из описания достаю основной текст
            repos_about_text = response.css('div.BorderGrid-cell p[class="f4 my-3"]::text').get()
            repos_about =  str(repos_about_text).strip() + " " + str(repos_about_link).strip()
        else:
            repos_about = repos_about.strip()
            repos_url_from_about == None
        site_url = response.css('div.BorderGrid-cell div[class="my-3 d-flex flex-items-center"] a::attr("href")').get() 
        if site_url == None:
            site_url = repos_url_from_about
            if site_url == None:
                site_url = 'Project Site Link Not Exist' #если невозможно получить ссылку из ссылки и/или из описания
        stars = response.css('div.BorderGrid-cell div[class="mt-2"] a strong::text')[0].get().strip()
        watching = response.css('div.BorderGrid-cell div[class="mt-2"] a strong::text')[1].get().strip()
        forks = response.css('div.BorderGrid-cell div[class="mt-2"] a strong::text')[2].get().strip()
        
        res = {
            'repos_name' : repos_name,
            'repos_about' : repos_about,
            'site_url' : site_url,
            'stars' : stars,
            'watching' : watching,
            'forks' : forks
        }
        # print(res)
        # yield res # при запуске с параметрами работает, выводит в json
#________________________________________________________________________________________________________________
        release_block_in_rep_page = response.css('div[class="BorderGrid BorderGrid--spacious"] div.BorderGrid-cell')[1]
        releases_counter = release_block_in_rep_page.css('span::attr("title")').get()
        #если в блоке релиза, есть информация по кол-ву - переходим в последний релиз, собираем по нему инфу
        if releases_counter != None:
            # print(releases_counter)
            url_last_release = response.url+'/releases/latest'
            res_tags = {'my_data' : res}
            yield response.follow(url_last_release,callback=self.parse_releases_page,meta=res_tags)
        # *НО релизы могут быть просто тегированы, без информаци на общей странице релизов
        # на примере https://github.com/vmware/pyvcloud
        else: 
            #пробую получить информацию из тегированного релиза
            releases_counter = release_block_in_rep_page.css('span.text-bold::text').get()
            if releases_counter == None: #если и здесь None - Релизы отстствуют
                releases_counter = "Releases Not Exist"
            else: #требуется получить информацию по последнему релизу на странице тегов
                url_tags = response.url+"/tags"
                res_tags = {'my_data' : res}
                yield response.follow(url_tags,callback=self.parse_tages_page,meta=res_tags)
        # print(repos_name,releases_counter)
        # print(response.meta)

#________________________________________________________________________________________________________________
        # для получения информации по ПОСЛЕДНЕМУ комиту(за исключением их кол-ва), требуется переход по ссылке последнего коммита.
        commit_info = response.css('div[class="js-details-container Details d-flex rounded-top-2 flex-items-center flex-wrap"]')
        commit_count = commit_info.css('div.flex-shrink-0 ul li a strong::text').get()
        last_commit_link = commit_info.css('a[data-test-selector="commit-tease-commit-message"]::attr("href")').get()
        if last_commit_link == None:
            last_commit_link = commit_info.css('include-fragment::attr("src")').get().replace("/tree-","/")
        
        yield response.follow(last_commit_link,callback=self.parse_last_commit_page)
        
        # print(repos_name," : ",repos_about," : ",stars," : ",watching," : ",forks)
    
    def parse_last_commit_page(self,response):
        last_commit_author = response.css('a.commit-author::text').get()
        last_commit_name = response.css('div.commit-title::text').get()
        last_commit_date = response.css('relative-time::attr("datetime")').get()
        print(last_commit_author,last_commit_name,last_commit_date)
    
    def parse_releases_page(self, response):
        #если релизы НЕ сущетвую то линк остаётся : /releases
        #если существует то выполняется редирект на /releases/tag/release
        if 'tag' in response.url:
            release_version = response.css('h1[class="d-inline mr-3"]::text').get()
            release_change_log = response.css('div[class="markdown-body my-3"]').get()
            release_change_log_html = lxml.html.fromstring(release_change_log) #что бы получить весь текст из блока changlog
            release_change_log = f" {release_change_log_html.text_content().strip()} "
            release_datetime = response.css('relative-time::attr("datetime")').get()
            if release_datetime == None:
                release_datetime = response.css('local-time::attr("datetime")').get()
        data={}
        data['release_version'] = release_version
        data['release_change_log'] = release_change_log
        data['release_datetime'] = release_datetime
        yield data

    def parse_tages_page(self,response):
        #зайдя на страницу тегов
        info_from_tags_page = response.css('div[class="Box-body p-0"]')
        #получаю имя последнего релиза
        last_release_info = info_from_tags_page.css('div[class="Box-row position-relative d-flex "]')[0]
        release_name = last_release_info.css('a::text')[0].get().strip()
        #на основании имени делаю ссылку на сам релиз
        link_to_last_release_in_tags = (response.url).replace('/tags',f'/releases/tag/{release_name}')
        yield response.follow(link_to_last_release_in_tags,callback=self.parse_releases_page_from_tags,meta=response.meta['my_data'])
    
    def parse_releases_page_from_tags(self, response):
        # print(response.meta)
        release_version = (response.url).split("/")[-1]
        release_datetime = response.css('div[class="col-12 col-md-9 col-lg-10 px-md-3 py-md-4 release-main-section commit open float-left"] div.release-header local-time::attr(datetime)').get()
        release_change_log = response.css('div[class="col-12 col-md-9 col-lg-10 px-md-3 py-md-4 release-main-section commit open float-left"] div[class="commit-desc border-bottom pb-3"] pre::text').get()
        data={}
        data['release_version'] = release_version
        data['release_change_log'] = release_change_log
        data['release_datetime'] = release_datetime
        yield data
            


