var _qrt = require("datawire-quark-core");
var testlib = require('../testlib');
exports.testlib = testlib;



function test() {
    /* import testlib */

    var f = testlib.foo();
    _qrt.print(f);
}
exports.test = test;
