// JS Hello Client Example
/* jshint node: true */

"use strict";

var datawire_connect = require('datawire_connect').datawire_connect;
var DatawireState = datawire_connect.state.DatawireState;
var DWCResolver = datawire_connect.resolver.DiscoveryConsumer;

var datawire_discovery = require('discovery_1_0_0').datawire_discovery;
var DWCOptions = datawire_discovery.client.GatewayOptions;

var hello = require("hello").hello;

/******** Mainline ********/
// We're going to send a string over to the "hello" RPC service, so we'll start
// by checking our command-line arguments to see if the user wants to override
// that string.

var process = require("process");
var args = process.argv.splice(process.execArgv.length + 2);

var text = "Hello from JavaScript";

if (args.length > 0) {
    text = args[0];
}

// Grab our service token.
var dwState = DatawireState.defaultState();
var token = dwState.getCurrentServiceToken("hello");

// Set up the client...
var client = new hello.HelloClient("hello");

// ...and tell it that we want to use Datawire Connect to find providers of
// this service.
var options = new DWCOptions(token);
client.setResolver(new DWCResolver(options));

// Every five seconds, we'll say hello.
var reqNo = 0;

function sendRequest() {
    reqNo++;

    var request = new hello.Request();
    request.text = text;

    console.log("\n" + reqNo + ": sending " + request.text);

    var response = client.hello(request);

    response.onFinished({
        onFuture: function(response) {
            if (response.getError() !== null) {
                console.log(reqNo + ": failed! " + response.getError());
            } else {
                console.log(reqNo + ": received " + response.result);
            }
        }
    });

    setTimeout(sendRequest, 5000);
}

setTimeout(sendRequest, 5000);
