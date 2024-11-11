from pymavlink import mavutil
import time

# Function to fix MAVLink messages containing strings
def fixMAVLinkMessageForForward(msg):
    msg_type = msg.get_type()
    if msg_type in ('PARAM_VALUE', 'PARAM_REQUEST_READ', 'PARAM_SET'):
        if type(msg.param_id) == str:
            msg.param_id = msg.param_id.encode()
    elif msg_type == 'STATUSTEXT':
        if type(msg.text) == str:
            msg.text = msg.text.encode()
    return msg

# Set up connections
ark = mavutil.mavlink_connection('/dev/serial/by-id/usb-ARK_ARK_FMU_v6X.x_0-if00', baud=115200)
print('Waiting for ARK heartbeat...')
ark.wait_heartbeat()
print('Established connection to ARK')

trip = mavutil.mavlink_connection('0.0.0.0:14549', baud=115200)
print('Opened connection to TRIP')

gcs_conn = mavutil.mavlink_connection('0.0.0.0:14550')
print('Opened connection to GCS')

last_trip_heartbeat = time.time()

while True:
    # Process messages from GCS
    gcs_msg = gcs_conn.recv_match(blocking=False)
    if gcs_msg and gcs_msg.get_type() != 'BAD_DATA' and gcs_msg.get_type().find('UNKNOWN') == -1:
        gcs_msg = fixMAVLinkMessageForForward(gcs_msg)

        # Forward all messages from GCS to ARK
        ark.mav.srcSystem = gcs_msg.get_srcSystem()
        ark.mav.srcComponent = gcs_msg.get_srcComponent()
        try:
            ark.mav.send(gcs_msg)
            print('GCS --> ARK:', gcs_msg.get_type())
        except Exception as e:
            print(f'Error forwarding {gcs_msg.get_type()} from GCS to ARK: {e}')

        # Forward COMMAND_LONG messages from GCS to TRIP
        if gcs_msg.get_type() == 'COMMAND_LONG' and time.time() - last_trip_heartbeat <= 2:
            trip.mav.srcSystem = gcs_msg.get_srcSystem()
            trip.mav.srcComponent = gcs_msg.get_srcComponent()
            try:
                trip.mav.send(gcs_msg)
                print('GCS --> TRIP: COMMAND_LONG')
            except Exception as e:
                print(f'Error forwarding COMMAND_LONG from GCS to TRIP: {e}')

    # Process messages from TRIP
    if trip:
        trip_msg = trip.recv_match(blocking=False)
        if trip_msg and trip_msg.get_type() != 'BAD_DATA' and trip_msg.get_type().find('UNKNOWN') == -1:
            trip_msg = fixMAVLinkMessageForForward(trip_msg)

            # Forward COMMAND_ACK and V2_EXTENSION messages from TRIP to GCS
            if trip_msg.get_type() in ['COMMAND_ACK', 'V2_EXTENSION']:
                gcs_conn.mav.srcSystem = trip_msg.get_srcSystem()
                gcs_conn.mav.srcComponent = trip_msg.get_srcComponent()
                try:
                    gcs_conn.mav.send(trip_msg)
                    print('TRIP --> GCS:', trip_msg.get_type())
                except Exception as e:
                    print(f'Error forwarding {trip_msg.get_type()} from TRIP to GCS: {e}')

            # Track TRIP heartbeat for connection monitoring
            if trip_msg.get_type() == 'HEARTBEAT':
                last_trip_heartbeat = time.time()

    # Process messages from ARK
    ark_msg = ark.recv_match(blocking=False)
    if ark_msg and ark_msg.get_type() != 'BAD_DATA' and ark_msg.get_type().find('UNKNOWN') == -1:
        ark_msg = fixMAVLinkMessageForForward(ark_msg)

        #Forward all messages from ARK to GCS, except COMMAND_ACK when TRIP is active
        if not (ark_msg.get_type() == 'COMMAND_ACK' and time.time() - last_trip_heartbeat <= 2):
            gcs_conn.mav.srcSystem = ark_msg.get_srcSystem()
            gcs_conn.mav.srcComponent = ark_msg.get_srcComponent()
            try:
                gcs_conn.mav.send(ark_msg)
                print(f'ARK --> GCS: {ark_msg.get_type()}')
            except Exception as e:
                print(f'Error forwarding {ark_msg.get_type()} from ARK to GCS: {e}')

    # Prevent CPU overload
    time.sleep(0.001)
