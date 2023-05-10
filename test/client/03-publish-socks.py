#!/usr/bin/env python3

#

from mosq_test_helper import *

def do_test(proto_ver, host):
    rc = 1

    (port1, port2) = mosq_test.get_port(2)

    cmd = ['microsocks', '-?']
    try:
        proxy = subprocess.run(cmd, capture_output=True)
    except FileNotFoundError:
        print("microsocks not found, skipping test")
        sys.exit(0)

    cmd = ['microsocks', '-1', '-i', host, '-u', 'user', '-P', 'password', '-p', str(port1)]
    if b"bindaddr" in proxy.stderr:
        cmd += ['-b', host]
    else:
        cmd += ['-b']

    try:
        proxy = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("microsocks not found, skipping test")
        sys.exit(0)

    if proto_ver == 5:
        V = 'mqttv5'
    elif proto_ver == 4:
        V = 'mqttv311'
    else:
        V = 'mqttv31'

    env = {
            'LD_LIBRARY_PATH': mosq_test.get_build_root() + '/lib',
            'XDG_CONFIG_HOME':'/tmp/missing'
            }
    cmd = [
            '../../client/mosquitto_pub',
            '-h', host,
            '-p', str(port2),
            '-q', '1',
            '-t', '03/pub/proxy/test',
            '-m', 'message',
            '-V', V,
            '--proxy', f'socks5h://user:password@{host}:{port1}'
            ]

    mid = 1
    publish_packet = mosq_test.gen_publish("03/pub/proxy/test", qos=1, mid=mid, payload="message", proto_ver=proto_ver)
    if proto_ver == 5:
        puback_packet = mosq_test.gen_puback(mid, proto_ver=proto_ver, reason_code=mqtt5_rc.MQTT_RC_NO_MATCHING_SUBSCRIBERS)
    else:
        puback_packet = mosq_test.gen_puback(mid, proto_ver=proto_ver)

    broker = mosq_test.start_broker(filename=os.path.basename(__file__), port=port2, checkhost=host)

    try:
        sock = mosq_test.sub_helper(port=port2, topic="#", qos=1, proto_ver=proto_ver)

        pub = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        pub_terminate_rc = 0
        if mosq_test.wait_for_subprocess(pub):
            print("pub not terminated")
            pub_terminate_rc = 1
        (stdo, stde) = pub.communicate()

        mosq_test.expect_packet(sock, "publish", publish_packet)
        rc = pub_terminate_rc
        sock.close()
    except mosq_test.TestError:
        pass
    except Exception as e:
        print(e)
    finally:
        proxy.terminate()
        broker.terminate()
        if mosq_test.wait_for_subprocess(broker):
            print("broker not terminated")
            if rc == 0: rc=1
        (stdo, stde) = broker.communicate()
        if rc:
            print(stde.decode('utf-8'))
            print("proto_ver=%d" % (proto_ver))
            exit(rc)


do_test(proto_ver=3, host="localhost")
do_test(proto_ver=4, host="localhost")
do_test(proto_ver=5, host="localhost")
do_test(proto_ver=5, host="ip6-localhost")
do_test(proto_ver=5, host="127.0.0.1")
#do_test(proto_ver=5, host="::1")
