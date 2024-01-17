# import boto3
import json
import requests


class LambdaProcessor(object):

    def __init__(self):
        # self.aws_client = boto3.client('lambda', "")
        self.lambda_function = "test"

    # def request_lambda(self, url_list):
    #     invoke_response = self.aws_client.invoke(FunctionName=self.lambda_function, Payload=json.dumps(url_list))
    #     data_binary = invoke_response['Payload'].read()
    #     data_str = bytes.decode(data_binary)
    #     data_dict = json.loads(data_str)
    #     return data_dict

    def request(self, url_list):
        return_data = []
        for url in url_list:
            print(url['url'])
            if url['parser_name'] == "special":
                res_data = requests.get(url['url']).text
            elif url['parser_name'] == "PttCrawler:parse":
                res_data = requests.get(url['url'], cookies={'over18': '1'}).text
            else:
                res_data = requests.get(url['url']).text

            return_data.append({"url": url['url'],
                                "html": res_data,
                                "parser_name": url['parser_name'],
                                "uid": url['uid']})
        return return_data


if __name__ == '__main__':
    lp = LambdaProcessor()
    r = lp.request([{"url": "https://www.ptt.cc/bbs/Gossiping/index.html",
                     "parser_name": "PttCrawler:parse", "uid": "123"}])
    print(r[0]['html'])
