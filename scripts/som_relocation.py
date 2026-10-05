import random
import urllib.parse

import requests

som_url = "http://localhost:8081/api/v2/"
key = "paste-your-token-here"  # token returned by POST /api/v2/loginViaBasic


def subscription_lookup(subscription_id, key):
    while subscription_id == "":
        subscription_id = input("Enter the subscription ID again: ")
    url = som_url + "suscripciones/" + subscription_id + "?" + urllib.parse.urlencode({"key": key})
    replydata = requests.get(url)
    json_data = replydata.json()
    json_status = replydata.status_code
    if json_status == 200:
        client = json_data["cliente_id"]
        service = json_data["tipo_servicio"]
        status = json_data["estado"]
        print("Subscription API URL for " + subscription_id + " (Service: " + service + ", Status: " + status + ")\n" + url)
    else:
        client = "null"
        service = "null"
        status = "null"
        print("Subscription API status: " + str(json_status) + "\nError message: " + json_data["error"]["mensaje"])
    return json_status, client, service, subscription_id


def point_parse(text):
    parts = text.split(",")
    if len(parts) < 2:
        print("Invalid point. Use the format x,y or x,y,reference (example: 2.5,1.75,Living)")
        return None
    try:
        point = {"x": float(parts[0]), "y": float(parts[1])}
    except ValueError:
        print("Invalid point. x and y must be numbers (example: 2.5,1.75)")
        return None
    if len(parts) > 2 and parts[2].strip() != "":
        point["referencia"] = parts[2].strip()
    return point


while True:
    print("\n+++++++++++++++++++++++++++++++++++++++++++++")
    print("Priorities available on SOM:")
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    print("ALTA, MEDIA, BAJA")
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    priorities = ["ALTA", "MEDIA", "BAJA"]
    priority = input("Enter a priority from the list above: ")
    if priority == "quit" or priority == "q":
        break
    elif priority in priorities:
        priority = priority
    else:
        priority = "MEDIA"
        print("No valid priority was entered. Using the MEDIA priority.")
    sub = input("Subscription ID: ")
    if sub == "quit" or sub == "q":
        break
    subscription = subscription_lookup(sub, key)
    loc1 = input("Current point (x,y,reference): ")
    if loc1 == "quit" or loc1 == "q":
        break
    orig = point_parse(loc1)
    loc2 = input("Destination point (x,y,reference): ")
    if loc2 == "quit" or loc2 == "q":
        break
    dest = point_parse(loc2)
    print("=================================================")
    if subscription[0] == 200 and orig is not None and dest is not None:
        order = {
            "tipo_orden": "RELOCALIZACION",
            "com_id": str(random.randint(1000000, 9999999)),
            "cliente_id": subscription[1],
            "subscription_id": subscription[3],
            "punto_actual": orig,
            "punto_destino": dest,
            "prioridad": priority,
        }
        order_url = som_url + "ordenes?" + urllib.parse.urlencode({"key": key})
        order_reply = requests.post(order_url, json=order)
        order_status = order_reply.status_code
        order_data = order_reply.json()
        print("Order API Status: " + str(order_status) + "\nOrder API URL:\n" + order_url)
        print("=================================================")
        if order_status == 201:
            trace_url = som_url + "ordenes/" + order_data["id"] + "/trazabilidad?" + urllib.parse.urlencode({"key": key})
            trace_status = requests.get(trace_url).status_code
            trace_data = requests.get(trace_url).json()
            print("Trace API Status: " + str(trace_status) + "\nTrace API URL:\n" + trace_url)
            print("=================================================")
            print("Relocation of subscription " + subscription[3] + " (" + subscription[2] + ") with priority " + priority)
            print("=================================================")
            if trace_status == 200:
                meters = trace_data["trabajo"]["distancia_m"]
                centimeters = trace_data["trabajo"]["distancia_m"] * 100
                sec = int(trace_data["trabajo"]["duracion_estimada_ms"] / 1000 % 60)
                mins = int(trace_data["trabajo"]["duracion_estimada_ms"] / 1000 / 60 % 60)
                hr = int(trace_data["trabajo"]["duracion_estimada_ms"] / 1000 / 60 / 60)
                print("Cable Length: {0:.1f} m / {1:.1f} cm".format(meters, centimeters))
                print("Work Duration: {0:02d}:{1:02d}:{2:02d}".format(hr, mins, sec))
                print("=================================================")
                for each in range(len(trace_data["trabajo"]["pasos"])):
                    step = trace_data["trabajo"]["pasos"][each]["texto"]
                    distance = trace_data["trabajo"]["pasos"][each]["distancia_m"]
                    print("{0} ( {1:.1f} m / {2:.1f} cm )".format(step, distance, distance * 100))
                print("=============================================")
            else:
                print("Error message: " + trace_data["error"]["mensaje"])
                print("*************************************************")
        else:
            print("Error message: " + order_data["error"]["mensaje"])
            print("*************************************************")
