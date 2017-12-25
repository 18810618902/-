import smtplib
from email.mime.text import MIMEText
from email.header import Header


def email_notice(content):
    sender = 'cangzhoufu@126.com'
    password = 'fastweb1605'
    subject = "TX_CDN - BEIAN Status Summary"
    fromaddr = "cangzhoufu@126.com"
    toaddrs = [
                 'jin.wang@txnetworks.cn',
                 ]

    subject = "备案结果通知"
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = fromaddr
    msg['To'] = "jin.wang@txnetworks.cn"

    try:
        smtpObj = smtplib.SMTP('smtp.126.com')
        #smtpObj.set_debuglevel(1)
        smtpObj.login(sender, password)
        smtpObj.sendmail(sender, toaddrs, msg.as_string())
        print("send email successful!!!")

    except smtplib.SMTPException as e:
        print("Error: send mail false,for detail:%s",e)

