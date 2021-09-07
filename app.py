from bson import decimal128
from flask import Flask,render_template,request,url_for,session
from flask.templating import render_template_string
from werkzeug.utils import redirect
from flask_session import Session
from bson import ObjectId # For ObjectId to work
from bson.objectid import ObjectId
from bson.decimal128 import Decimal128, create_decimal128_context
import decimal
import pymongo
import bcrypt
import pandas as pd
from datetime import datetime
import calendar
import pygal
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
# reading the price and product from grocery sheet
dat=pd.read_csv('Grocery.csv')
dat=dat.values.tolist()
li=[]
mi=[]
st=[]
pr=[]
#treshold = 3
#db connection
mongo = pymongo.MongoClient('mongodb+srv://Salman:salman@cluster0.kjvnu.mongodb.net/chef_at_home_testing?retryWrites=true&w=majority', tls=True, tlsAllowInvalidCertificates=True)

db = pymongo.database.Database(mongo, 'chef_at_home_testing')
col = pymongo.collection.Collection(db, 'supplierlogin')
col1=pymongo.collection.Collection(db, 'companylogin')
ind=pymongo.collection.Collection(db, 'items')
ai=pymongo.collection.Collection(db, 'add_item')
inv=pymongo.collection.Collection(db,'inventory')
inv_cred = pymongo.collection.Collection(db, 'inventory_login_cred')
inv_item_ingredients = pymongo.collection.Collection(db, 'inv_item_ingredients')
prod_to_item_map = pymongo.collection.Collection(db, 'prod_to_dish_map')
csession=[]

x=ind.find()
for data in x:
    li.append(data)

#initializing flask
app=Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
#initializing session
Session(app)
Session(app)
#render to homepage
@app.route('/')
def home():
    return render_template('home.html')

#choose whether supplier or company
@app.route('/input', methods=['GET','POST'])
def input():
    if request.method=="POST":
        details=request.form
        #fectching th data
        print(details)
        details=details.getlist("findItems")
        print(details)
        domain=str(details[0])

        if domain=="SUPPLIER":
            return render_template('slogin.html')
        elif domain=="INVENTORY":
            return render_template("inven_login.html",msg="")
        else:
            return render_template('clogin.html')
#add stock totally
@app.route('/cmain',methods=['GET','POST'])
def cmain():
    #create dictionary
    dict={}
    cost=0
    if request.method=="POST":
        for i in mi:

            if i[0] in dict:
                dict[i[0]]+=i[1]
            else:
                dict[i[0]]=i[1]
        print(dict)
        #push the data into collection
        for i in dict:
            for j in range(len(dat)):
                if dat[j][0]==i:
                    #fetching price of item
                    cost=dat[j][1]
                js={"product":i,"quantity":dict[i],"date":datetime.now().isoformat() ,"status":"Entered","cost":cost*dict[i]}
                #inserting one by one
                ai.insert_one(js)
                break
        mi.clear()
        return render_template('cindex.html')

@app.route('/cpass')
def cpass():
    return render_template('cpass.html')

#chaange password for company
@app.route('/cpassword',methods=['GET','POST'])
def cpassword():
    msg=""
    l=[]
    if request.method=="POST":
        details=request.form
        #fetch the data
        name=details['name']
        passw=details['pass']
        npass=details['npass']
        #search for password and name if name and password in collection allow them to change password
        login_user=col1.find_one({'name':name})
        upass=login_user['password']
        uname=login_user['name']
        if uname==name and upass==passw:
            #update command
            myquery = { "password": passw }
            newvalues = { "$set": { "password": npass } }
            col1.update_one(myquery, newvalues)
            msg="Password Updated Sucessfully!!!"
            return render_template('clogin.html',msg=msg)
        else:
            msg="Invalid Credentials !! Try Again"
            return render_template('cpass.html',msg=msg)

@app.route('/spass')
def spass():
    return render_template('spass.html')


#chaange password for supplier
@app.route('/spassword',methods=['GET','POST'])
def spassword():
    msg=""
    if request.method=="POST":
        details=request.form
        name=details['name']
        passw=details['pass']
        npass=details['npass']
        login_user=col.find_one({'name':name})
        upass=login_user['password']
        uname=login_user['name']
        #search for password and name if name and password in collection allow them to change password
        if uname==name and upass==passw:
            myquery = { "password": passw }
            newvalues = { "$set": { "password": npass } }
            col.update_one(myquery, newvalues)
            msg="Password Updated Sucessfully!!!"
            return render_template('slogin.html',msg=msg)
        else:
            msg="Invalid Credentials !! Try Again"
            return render_template('spass.html',msg=msg)

#logout part for supplier
@app.route('/supplierindex')
def sindex():
    print(session)
    session.pop('name',None)
    print(session)
    return render_template('slogin.html')

#logout part for company
@app.route('/companyindex')
def cindex():
    print(csession)
    if csession:
        csession.pop()
    print(csession)
    return render_template('clogin.html')

#view stock part
@app.route('/vstock')
def vstock():
    #fetch the data
    x=ind.find()
    #converting into table format
    data=pd.DataFrame(x)
    data=data.iloc[: , 1:]
    data.columns=['Items','Price']
    return render_template('viewstock.html',tables=data.to_html(classes='data'))


#remove stock part
@app.route('/remove', methods=['GET','POST'] )
def remove():
    if request.method=="POST":
        ms=""
        details=request.form
        n=int(details['no'])
        print(n)
        #match case
        if n in range(0,len(mi)):
            mi.pop(n)
            ms="ITEM REMOVED SUCCESSFULLY"
        #unmatch case
        else:
            ms="ITEM NUMBER NOT EXIST, SO CAN'T REMOVE"
        print(mi)
        return render_template('addstock.html',tbl=mi,ms=ms,li=li)



#add stock page
@app.route('/stock', methods=['GET','POST'])
def stock():
    msg=""
    if request.method=="POST":
        details=request.form
        #fetch data
        pro=details['name']
        quan=int(details['pass'])
        mi.append([pro,quan])
        #new=pd.DataFrame(mi,columns=['PRODUCT','QUANTITY'])
        #js={"product":pro,"quantity":quan,"date":datetime.now()}
        #ai.insert_one(js)
        msg="ITEM ADDED SUCCESSFULLY"
        return render_template('addstock.html',tbl=mi,msg=msg,li=li)

#previously purchased stock
@app.route('/previous', methods=['GET','POST'])
def previous():
    lis=[]
    if request.method=="POST":
        details=request.form
        #getting from date
        d1=details['from']
        date1=datetime.strptime(d1, '%Y-%m-%d')
        #getting two date
        d2=details['to']
        date2=datetime.strptime(d2, '%Y-%m-%d')
        print(date1,date2)
        start = date1.date()
        #from date
        start=str(start)+'T0'
        #end date
        end = date2.date()
        end=str(end)+'T23'
        print(start,end)
        #search in collection
        find = ai.find({ '$and' : [ { 'date' : {'$gte' : start } } , { 'date' : { '$lte' : end }}]},{'_id':0,'product':1,'quantity':1,'status':1})
        for x in find:
            if x['status']=="Approved":
                pro=[x['product'],x['quantity'],x['status']]
                lis.append(pro)
        print(lis)
        return render_template('previousstock.html',tbl=lis)


@app.route('/back')
def back():
    return render_template('cindex.html')

@app.route("/supplier_back")
def supplier_back():
    return render_template('sindex.html')

#appreoved stock
@app.route('/astock')
def astock():
    stock=[]
    #todat date
    d=datetime.today().strftime('%Y-%m-%d')
    start = d +'T0'
    #find all the approved stock mand appending in list stock
    find = ai.find({  'date' : { '$gte': start } },{'_id':0,'product':1,'quantity':1,'status':1,'delivery':1,'reason':1})
    for x in find:
        s=[x['product'],x['quantity'],x['status'],x['delivery'],x['reason']]
        stock.append(s)
    return render_template('viewapproval.html',tbl=stock)

@app.route('/smain', methods=['GET','POST'])
def smain():
    if request.method=="POST":
        details=request.form
        val=int(details.getlist("findItems")[0])
        print(val,type(val))
        if val==1:
            return redirect(url_for("stockapprove"))
        elif val==2:
            x=ind.find()
            for data in x:
                pr.append(data)
            return render_template('priceedit.html',li=pr)
        else:
            return render_template('previousstock.html')

#stock approve
@app.route('/stockapprove', methods=['GET','POST'])
def stockapprove():
    #today date
    print("list st is ===>",st)
    while st:
        st.pop()
    d=datetime.today().strftime('%Y-%m-%d')
    start = d +'T0'
    #find the entered stock
    find = ai.find({  'date' : { '$gte': start } },{'_id':1,'product':1,'quantity':1,'status':1})
    for x in find:
        if x['status']=="Entered":
            st.append(x)
    for i in st:
        print(i['_id'])
    return render_template('stockapprove.html',tbl=st)

#supplier change the status approved or not approved
@app.route('/sa', methods=['GET', 'POST'])
def index():
    n=[]
    ap=[]
    if request.method == 'POST':
        #if supplier click check box it is approved else not approved
        res=request.form.getlist('mycheckbox')
        day=request.form.getlist('days')
        reason=request.form.getlist('reason')
        print(reason)
        print(day)
        j=0
        #approve stock status will be approved else we m,ake it not approved
        for i in st:
            myquery = { "_id": i['_id'] }
            newvalues = { "$set": { "delivery": day[j] } }
            ai.update_one(myquery, newvalues)
            myquery = { "_id": i['_id'] }
            newvalues = { "$set": { "reason": reason[j] } }
            ai.update_one(myquery, newvalues)
            j=j+1
        for i in st:
            print(str(i['_id']))
            if str(i['_id']) not in res:
                n.append(i['_id'])
        print(n)
        for i in res:
            c=0
            myquery = { "_id": ObjectId(i) }
            newvalues = { "$set": { "status": "Approved" } }
            ai.update_one(myquery, newvalues)
            find = ai.find_one({'_id': ObjectId(i)},{'product':1,'quantity':1})
            print(find['product'],find['quantity'])
            a=inv.find_one({'Item':find['product']},{'Quantity':1})
            c=a['Quantity']+find['quantity']
            query={"Item":find['product']}
            newval={ "$set": {"Quantity":c}}
            inv.update_one(query,newval)
        for i in n:
            myquery = { "_id": i }
            newvalues = { "$set": { "status": "Not Approved" } }
            ai.update_one(myquery, newvalues)

        return render_template('sindex.html')


@app.route('/commain', methods=['GET','POST'])
def commain():
    if request.method=="POST":
        details=request.form
        val=int(details.getlist("findItems")[0])
        print(val,type(val))
        if val==1:
            return render_template('addstock.html',li=li)
        elif val==2:
            return redirect(url_for("vstock"))
        elif val==3:
            return redirect(url_for("astock"))
        elif val==5:
            return redirect(url_for("view_inventory"))
        else:
            return render_template('previousstock.html')

#supplier login validation
@app.route('/slogin', methods=['GET','POST'])
def slogin():
    if request.method=="POST":
        msg=""
        details=request.form
        #fetching data
        name=str(details.getlist('uname')[0])
        password=str(details.getlist('psw')[0])
        #fetching data from collection
        login_user=col.find()
        for i in login_user:
            #match case
            if i['name']==name:
                if i['password']==password:
                    session["name"]=name
                    msg="Successfully Logged In"
                    return render_template('sindex.html',msg=msg)
                #unmatch case
                else:
                    msg="Invalid Password!!!"
                    return render_template('slogin.html',msg=msg)
        msg="Invalid Login Credential"
        return render_template('slogin.html',msg=msg)


@app.route('/dv', methods=['GET','POST'])
def dv():
    ab = ai.find({},{"_id":0,"product":1,"quantity":1}).sort([("quantity", -1)]).limit(10)
    data=list(ab)
        #data = pd.DataFrame(list(ab))
    print(data)
        #data.plot.bar(x="product", y="quantity", rot=70, title=" ");
        #plt.show(block=True);
    bar_chart = pygal.Bar(height=300)
    bar_chart.title = 'Top 10 Goods Purchased'
    for x in data:
        bar_chart.add(x['product'],x['quantity'])
    bar_chart = bar_chart.render_data_uri()
    return render_template('visual.html',ch=bar_chart)

#company login
@app.route('/clogin', methods=['GET','POST'])
def clogin():
   if request.method=="POST":
        msg=""
        #fetch the data
        details=request.form
        name=str(details.getlist('uname')[0])
        password=str(details.getlist('psw')[0])
        #fetch from collection
        login_user=col1.find()
        for i in login_user:
            #match case
            if i['name']==name:
                if i['password']==password:
                    csession.append(name)
                    msg="Successfully Logged In"
                    return render_template('cindex.html',msg=msg)
                #unmatch case
                else:
                    msg="Invalid Password!!!"
                    return render_template('clogin.html',msg=msg)
        msg="Invalid Login Credential"
        return render_template('clogin.html',msg=msg)

 #price edit
@app.route('/price', methods=['GET','POST'])
def priceedit():
    msg=""
    if request.method=="POST":
        details=request.form
        #fetch the data
        pro=details['name']
        price=int(details['price'])
        #changing new price
        myquery = { "ITEM": pro }
        newvalues = { "$set": { "Price": price } }
        ind.update_one(myquery, newvalues)
        msg="Price changed Sucessfully"
        return render_template('priceedit.html',msg=msg,li=pr)


@app.route('/invoice', methods=['GET','POST'])
def invoice():
    bill=[]
    msg=""
    d=datetime.today().strftime('%Y-%m-%d')
    start = d +'T0'
    find = ai.find({  'date' : { '$gte': start } },{'date':1,'product':1,'quantity':1,'cost':1,'status':1})
    i=1
    pr=0
    for x in find:
        if x['status']=='Approved':
            bill.append([i,x['date'],x['product'],x['quantity'],x['cost']])
            i=i+1
            pr+=x['cost']
    DATA = [["S.NO","DATE" , "ITEM NAME", "QUANTITY", "PRICE (Rs.)" ]]
    for x in bill:
        DATA.append(x)
    DATA.append(["TOTAL","","","",pr])
    print(DATA)
    # creating a Base Document Template of page size A4
    pdf = SimpleDocTemplate( "receipt.pdf" , pagesize = A4 )

    # standard stylesheet defined within reportlab itself
    styles = getSampleStyleSheet()

    # fetching the style of Top level heading (Heading1)
    title_style = styles[ "Heading1" ]

    # 0: left, 1: center, 2: right
    title_style.alignment = 1

    # creating the paragraph with
    # the heading text and passing the styles of it
    title = Paragraph( "PROVISION BILL" , title_style )

    # creates a Table Style object and in it,
    # defines the styles row wise
    # the tuples which look like coordinates
    # are nothing but rows and columns
    style = TableStyle(
    [
        ( "BOX" , ( 0, 0 ), ( -1, -1 ), 1 , colors.black ),
        ( "GRID" , ( 0, 0 ), ( 4 , 4 ), 1 , colors.black ),
        ( "BACKGROUND" , ( 0, 0 ), ( 3, 0 ), colors.gray ),
        ( "TEXTCOLOR" , ( 0, 0 ), ( -1, 0 ), colors.whitesmoke ),
        ( "ALIGN" , ( 0, 0 ), ( -1, -1 ), "CENTER" ),
        ( "BACKGROUND" , ( 0 , 1 ) , ( -1 , -1 ), colors.beige ),
    ]
    )

    # creates a table object and passes the style to it
    table = Table( DATA , style = style )

    # final step which builds the
    # actual pdf putting together all the elements
    pdf.build([ title , table ])
    fromaddr = "Zangtechnical3@gmail.com"
    toaddr = "works.suryav@gmail.com"

    msg = MIMEMultipart()

    msg['From'] =fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Invoice Approval"

    body = "Please approve this invoice. To confirm , respond to this mail"

    msg.attach(MIMEText(body, 'plain'))

    filename = "receipt.pdf"
    attachment = open("receipt.pdf", "rb")

    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "@Zangers3")
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
    return render_template('cindex.html')



@app.route('/view_inventory' , methods=['GET','POST'])
def view_inventory():
    #if request.method == 'POST':

    return render_template("view_inventory.html",params=inv.find({}))
    #return redirect(url_for("home"))

@app.route("/inv_home", methods=['GET','POST'])
def inv_home():
    if request.method == 'POST':
        credentials = request.form
        print(credentials)

        inv_uname = credentials.getlist("uname")
        inv_password = credentials.getlist("psw")

        msg=""
        db_cred = inv_cred.find_one({})
        print(db_cred)
        print(inv_uname,inv_password)
        if db_cred["username"] == inv_uname[0]:
            if db_cred["password"] == inv_password[0]:
                return render_template("inv_index.html")
            else:
                return render_template("inven_login.html",msg="Invalid Password")
        else:
            return render_template("inven_login.html",msg="Invalid Username")


@app.route("/edit_inventory", methods=['GET','POST'])
def edit_inventory():
    return render_template("edit_inventory.html",params=inv.find({}))

@app.route("/edit_inv_items", methods=['GET','POST'])
def edit_inv_items():
    if request.method == "POST":

        myquery = {"_id": ObjectId(request.json["_id"])}
        newvalues = { "$set": { "Item":request.json["Item"] , "Quantity":float(request.json["Quantity"]),"Unit":request.json["Unit"]}}
        inv.update_one(myquery, newvalues)

        return "Succes"

@app.route("/remove_inv_items" , methods=['GET','POST'])
def remove_inv_items():
    if request.method == "POST":
        print(request.json)
        print(request)
        myquery = {"Item": request.json["Item"]}
        inv.delete_one(myquery)
        #inv_treshold.delete_one(myquery)
        print("After request")
        return "hello"

@app.route("/add_inv_items" , methods=['GET','POST'])
def add_inv_items():
    if request.method == "POST":
        print(request.json)
        print(request)
        myquery = {"Item": request.json["Item"],"Quantity":float( request.json["Quantity"]),"Treshold":float(request.json["Treshold"]),"Unit":request.json["Unit"]}
        inv.insert_one(myquery)
        #id = inv.find_one(myquery)["_id"]
        #inv_treshold.insert_one({"Item": request.json["Item"],"Treshold":3,"inv_id":id})
        print("After request")
        return "hello"


@app.route("/remove_inventory",methods=["GET","POST"])
def remove_inventory():
    return render_template("remove_inv.html",params=inv.find({},{"_id":1,"Item":1,"Quantity":1}))

@app.route("/add_inventory",methods=["POST","GET"])
def add_inventory():
    return render_template("add_inv.html")


@app.route("/change_set_treshold" , methods=["POST","GET"])
def change_set_treshold():
    if request.method == "POST":
        myquery = {"_id":ObjectId(request.json["_id"])}
        newvalues = {"$set": {"Treshold":int(request.json["Treshold"])}}
        print(myquery,newvalues,request.json)
        inv.update_one(myquery,newvalues)

        return "hello"

@app.route("/set_treshold", methods=["POST", "GET"])
def set_treshold():
    return render_template("set_treshold.html",params=inv.find({}))

@app.route("/set_treshold_password", methods=['POST'])
def set_treshold_password():
    if request.method == 'POST':
        cred_details = inv_cred.find_one()
        print(cred_details)
        id = cred_details['_id']
        myquery = {"_id":id}
        newvalues = { "$set": { "password":request.json["val"]}}
        inv_cred.update_one(myquery, newvalues)
        return "successfull"




@app.route("/order_placed", methods=['POST'])
def order_placed():
    if request.method=="POST":
        if request.json["api_key"] == "cah_zang":
            items = request.json["items"]

            for item in items:
                dish_name = item["p_name"]
                dish_qty = int(item["quantity"])
                item_arr = prod_to_item_map.find_one({"product_name":dish_name})["items"]
                for i in item_arr:
                    ingred = inv_item_ingredients.find_one({"Recipe":i})["Ingredients&Quantity"]

                    for key,val in ingred.items():
                        myquery = {"Item":key}
                        inv_qty_item = inv.find_one(myquery)["Quantity"]
                        newvalues = { "$set": {"Quantity":int(inv_qty_item)-(dish_qty * val)}}
                        inv.update_one(myquery, newvalues)



            return "Successfully"


        else:
            return "auth failed"



if __name__ == '__main__':
    app.run(debug=True)




#n_orders = request.json["n_orders"]
#            item_names = request.json["items"]
#           print(item_names)
#           for dic in item_names:
#              data = inv_item_ingredients.find_one({"Recipe":dic["item"]})
#              print("Data is",data)
#              print("================================")
#                print("next is",data["Ingredients&Quantity"].items())
#              for k,val in data["Ingredients&Quantity"].items():
#                   print("================================")
#                   print(inv)
#                    print("inside lpoop",int(inv.find_one({"Item":k})["Quantity"])-(n_orders*(val)))

#                    inv.update_one({"Item":k},{"$set":{"Quantity":int(inv.find_one({"Item":k})["Quantity"])-(n_orders*(val))}})
