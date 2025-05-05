"""
key: 2NJ64W9K7vQz6cqP
new_client_key: 55YS2V492NT2JKuBg8FnbP7GeW9b8A9cGnptbfbs2uG4p9Ky65Q7ZsWsqkj3uP87

request:
{
        "amount": 10.5,
        "card_number": "4111111111111111",
        "exp_date": "2026-12",
        "cvv": "123"
      }

response email:
========= SECURITY STATEMENT ==========
It is not recommended that you ship product(s) or otherwise grant services relying solely upon this e-mail receipt.

========= GENERAL INFORMATION =========
Merchant : Himanshu Sharma (929184)
Date/Time : 3-May-2025 8:07:08 PDT

========= ORDER INFORMATION =========
Invoice :
Description : Goods or Services
Amount : 10.50 (USD)
Payment Method: Visa xxxx1111
Transaction Type: Authorization and Capture

============== Line Items ==============

============== RESULTS ==============
Response : This transaction has been approved.
Auth Code : 6BC3UJ
Transaction ID : 120062511911
"""

from flask import Flask, request, jsonify
from authorizenet import apicontractsv1
from authorizenet.apicontrollers import *

app = Flask(__name__)

from dotenv import load_dotenv
import os

load_dotenv()  # Loads the .env file

MERCHANT_LOGIN_ID = os.getenv("MERCHANT_LOGIN_ID")
MERCHANT_TXN_KEY = os.getenv("MERCHANT_TXN_KEY")

import logging

logger = logging.getLogger('authorizenet.sdk')
handler = logging.FileHandler('anetSdk.log')
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.debug('Logger set up for Authorizenet Python SDK complete')

def get_auth():
    auth = apicontractsv1.merchantAuthenticationType()
    auth.name = MERCHANT_LOGIN_ID
    auth.transactionKey = MERCHANT_TXN_KEY
    return auth


def safe_getattr(obj, attr, default=None):
    try:
        return getattr(obj, attr)
    except AttributeError:
        return default


@app.route("/pay/one-time", methods=["POST"])
def one_time_payment():
    data = request.json
    amount = data["amount"]
    card_number = data["card_number"]
    exp_date = data["exp_date"]
    cvv = data["cvv"]

    credit_card = apicontractsv1.creditCardType()
    credit_card.cardNumber = card_number
    credit_card.expirationDate = exp_date
    credit_card.cardCode = cvv

    payment = apicontractsv1.paymentType()
    payment.creditCard = credit_card

    txn_request = apicontractsv1.transactionRequestType()
    txn_request.transactionType = "authCaptureTransaction"
    txn_request.amount = amount
    txn_request.payment = payment

    request_obj = apicontractsv1.createTransactionRequest()
    request_obj.merchantAuthentication = get_auth()
    request_obj.transactionRequest = txn_request

    controller = createTransactionController(request_obj)
    controller.execute()
    response = controller.getresponse()

    if response and response.messages.resultCode == "Ok":
        return jsonify({
            "status": "success",
            "transaction_id": str(response.transactionResponse.transId)
        })
    else:
        return jsonify({"status": "error", "message": response.messages.message[0].text}), 400


@app.route("/pay/recurring", methods=["POST"])
def recurring_payment():
    data = request.json
    try:
        amount = float(data.get("amount"))
        days = int(data.get("interval_days", 30))
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount or interval_days"}), 400

    # Build merchant auth
    merchantAuth = apicontractsv1.merchantAuthenticationType()
    merchantAuth.name = MERCHANT_LOGIN_ID
    merchantAuth.transactionKey = MERCHANT_TXN_KEY

    # Payment schedule
    from datetime import datetime, timedelta
    paymentschedule = apicontractsv1.paymentScheduleType()
    paymentschedule.interval = apicontractsv1.paymentScheduleTypeInterval()
    paymentschedule.interval.length = days
    paymentschedule.interval.unit = apicontractsv1.ARBSubscriptionUnitEnum.days
    paymentschedule.startDate = datetime(2030, 12, 30) # TODO: has to send the payment schedule start date
    paymentschedule.totalOccurrences = 12
    paymentschedule.trialOccurrences = 1

    # Card details
    creditcard = apicontractsv1.creditCardType()
    creditcard.cardNumber = data.get("card_number", "4111111111111111")
    creditcard.expirationDate = data.get("exp_date", "2035-12")

    payment = apicontractsv1.paymentType()
    payment.creditCard = creditcard

    # Billing info
    billto = apicontractsv1.nameAndAddressType()
    billto.firstName = data.get("first_name", "John")
    billto.lastName = data.get("last_name", "Smith")

    # Subscription
    subscription = apicontractsv1.ARBSubscriptionType()
    subscription.name = "Sample Subscription"
    subscription.paymentSchedule = paymentschedule
    subscription.amount = amount
    subscription.trialAmount = 0.00
    subscription.billTo = billto
    subscription.payment = payment

    # Request
    request_obj = apicontractsv1.ARBCreateSubscriptionRequest()
    request_obj.merchantAuthentication = merchantAuth
    request_obj.subscription = subscription

    controller = ARBCreateSubscriptionController(request_obj)
    controller.execute()
    response = controller.getresponse()

    if response is not None and response.messages.resultCode == "Ok":
        return jsonify({
            "amount": float(subscription.amount),
            "subscription_id": str(response.subscriptionId)
        })
    else:
        if response is not None and response.messages is not None:
            messages = response.messages.message
            if messages is not None and len(messages) > 0:
                err_msg = messages[0].text
                err_code = messages[0].code
            else:
                err_msg = "No error message returned"
                err_code = "None"
        else:
            err_msg = "Null or malformed response"
            err_code = "None"

        print("Error Code:", err_code)
        print("Error Message:", err_msg)
        return jsonify({"status": "error", "message": err_msg}), 400


@app.route("/pay/refund", methods=["POST"])
def refund_payment():
    data = request.json
    amount = data["amount"]
    last_four = data["last_four"]
    exp_date = data["exp_date"]
    trans_id = data["trans_id"]

    credit_card = apicontractsv1.creditCardType()
    credit_card.cardNumber = last_four
    credit_card.expirationDate = exp_date

    payment = apicontractsv1.paymentType()
    payment.creditCard = credit_card

    txn_request = apicontractsv1.transactionRequestType()
    txn_request.transactionType = "refundTransaction"
    txn_request.amount = amount
    txn_request.payment = payment
    txn_request.refTransId = trans_id

    request_obj = apicontractsv1.createTransactionRequest()
    request_obj.merchantAuthentication = get_auth()
    request_obj.transactionRequest = txn_request

    controller = createTransactionController(request_obj)
    controller.execute()
    response = controller.getresponse()

    if response and response.messages.resultCode == "Ok":
        return jsonify({
            "status": "success",
            "transaction_id": response.transactionResponse.transId
        })
    else:
        return jsonify({"status": "error", "message": response.messages.message[0].text}), 400


@app.route("/pay/status", methods=["GET"])
def get_payment_status():
    trans_id = request.args.get("trans_id")
    if not trans_id:
        return jsonify({"status": "error", "message": "Missing transaction ID"}), 400

    request_obj = apicontractsv1.getTransactionDetailsRequest()
    request_obj.merchantAuthentication = get_auth()
    request_obj.transId = trans_id

    controller = getTransactionDetailsController(request_obj)
    controller.execute()
    response = controller.getresponse()

    if response is not None and response.messages.resultCode == "Ok":
        txn = response.transaction

        customer_name = "N/A"
        if hasattr(txn, "customer") and txn.customer is not None:
            try:
                customer_name = txn.customer.firstName
            except AttributeError:
                pass

        return jsonify({
            "status": str(txn.transactionStatus),
            "amount": float(txn.settleAmount) if hasattr(txn, "settleAmount") and txn.settleAmount else 0.0,
            "payment_method": getattr(txn.payment, "method", "N/A") if hasattr(txn, "payment") else "N/A",
            "submitted_at": str(txn.submitTimeUTC) if hasattr(txn, "submitTimeUTC") else "N/A",
            "customer": customer_name
        })
    else:
        return jsonify({"status": "error", "message": response.messages.message[0].text}), 400


@app.route("/subscription/status", methods=["GET"])
def get_subscription_status():
    sub_id = request.args.get("sub_id")
    if not sub_id:
        return jsonify({"status": "error", "message": "Missing subscription ID"}), 400

    request_obj = apicontractsv1.ARBGetSubscriptionStatusRequest()
    request_obj.merchantAuthentication = get_auth()
    request_obj.subscriptionId = sub_id

    controller = ARBGetSubscriptionStatusController(request_obj)
    controller.execute()
    response = controller.getresponse()

    if response and response.messages.resultCode == "Ok":
        return jsonify({
            "status": response.status,
            "details": str(response.subscriptionId)
        })
    else:
        print("ERROR:")
        print("Message Code : %s" % response.messages.message[0]['code'].text)
        print("Message text : %s" % response.messages.message[0]['text'].text)
        return jsonify({"status": "error", "message": response.messages.message[0].text}), 400


if __name__ == "__main__":
    app.run(debug=True)
