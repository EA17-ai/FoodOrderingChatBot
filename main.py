from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from db import get_order_status, insert_order_item, get_next_order_id, get_total_order_price, insert_order_tracking
from generic_helper import extract_session_id, get_string_from_food_dict

app = FastAPI()

inprogress_orders = {}


@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    # print(payload)
    intent = payload["queryResult"]["intent"]["displayName"]
    # print("Received Intent:", intent)
    parameters = payload["queryResult"]["parameters"]
    print(parameters)
    output_contexts = payload["queryResult"]["outputContexts"]
    session_id = extract_session_id(output_contexts[0]["name"])
    if intent == "order.add  - context :ongoing-order":
        fulfillment_text = add_to_order(parameters, session_id)
        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })
    elif intent == "order.remove -context :ongoing-order":
        fulfillment_text = remove_from_order(parameters["food-item"], session_id)
        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

    elif intent == "order.complete  -context :ongoing-order":
        fulfillment_text = complete_order(parameters, session_id)

        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

    elif intent == "track.order - context: ongoing-tracking":
        order_id = int(parameters["order_id"])
        order_status = track_order(parameters)
        print(order_status)
        if order_status is not None:
            fulfillment_text = f"The order status for {order_id} is {order_status}"
        else:
            fulfillment_text = f"No such order {order_id}"
        print(fulfillment_text)
        return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })


def track_order(parameters: dict):
    # print(parameters)
    order_id = int(parameters["order_id"])
    status = get_order_status(order_id=order_id)
    return status


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        fulfillmentText = "I'm having trouble in finding your order .Sorry! Can you place a new order"
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fulfillmentText = "Sorry i couldnt process your order due to bacend error,Please place new order"
        else:
            order_total = get_total_order_price(order_id)
            fulfillmentText = f"Order placed successfully...here is your order_id {order_id} and total price for your " \
                              f"order is {order_total}..Pay at the time of delivery "
        del inprogress_orders[session_id]
    return fulfillmentText


def save_to_db(order: dict):
    next_order_id = get_next_order_id()
    for food_item, quantity in order.items():
        rcode = insert_order_item(
            food_item,
            quantity,
            next_order_id
        )
    if rcode == -1:
        return -1
    insert_order_tracking(next_order_id, "in progress")
    return next_order_id


def remove_from_order(parameters: list, session_id: str):
    if session_id:
        for item in parameters:
            if item in inprogress_orders[session_id].keys():
                del inprogress_orders[session_id][item]
            else:
                fulfillmentText=f"{item} specified is not in your order list"
                return fulfillmentText
        if bool(inprogress_orders[session_id]):
            fulfillmentText = f"Items specified are removed.So far you have ordered {get_string_from_food_dict(inprogress_orders[session_id])}," \
                              f"Would you like to add anything to your order"
        else:
            fulfillmentText = f"Your Order list is empty... would you like to add anything?"
    else:
        fulfillmentText = f"There is no order.Create a new order"

    return fulfillmentText


def add_to_order(parameters: dict, session_id: str):
    quantities = parameters["number"]
    food_items = parameters["food-item"]
    # print(food_items)
    # print(quantities)
    if len(food_items) != len(quantities):
        fulfillmentText = "Hey.I didn't understand.Can you please provide in this format:2 idli and 1 dosa"
    else:
        new_food_dict = dict(zip(food_items, quantities))
        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            for item, quantity in new_food_dict.items():
                if item in current_food_dict:
                    current_food_dict[item] += quantity
                else:
                    current_food_dict[item] = quantity

            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict
            print(inprogress_orders)
        fulfillmentText = f"So far you have ordered {get_string_from_food_dict(inprogress_orders[session_id])}, " \
                          f"Would you like anything more?"

    return fulfillmentText
