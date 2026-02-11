
const data = document.currentScript.attributes;
const jsonurl = data.getNamedItem('jsonurl').value;
const target = data.getNamedItem('target').value;
debugger

// Create our number formatter.
const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
});

var chartDom = document.getElementById(target);
var myChart = echarts.init(chartDom);
let tooltip_callback = (args) => {
    debugger;
    let mytooltip = args[0].axisValue + '<br />';
    let total = 0;
    for(let argN = 0; argN < args.length; ++ argN)
        {
            let arg = args[argN];
            mytooltip = mytooltip + '<div style="float: left;">' + arg.marker + ' ' + arg.seriesName  + ':  </div>   <div style="float: right;"><b > ' + formatter.format(arg.value) + '</b> </div><br />'; 
            total = total + parseFloat(arg.value);
        }
    mytooltip = mytooltip + '<div style="float: left;">  Total: </div>   <div style="float: right;"><b > ' +  formatter.format(total) + '$</b>';
    return mytooltip;
}
let option;
$(document).ready(function(){
    $.getJSON(jsonurl, function(data) {
            option = data
            option = Object.assign({
                tooltip: {
                    trigger: 'axis',
                    formatter: tooltip_callback
                    }
                }, 
                option )
            option && myChart.setOption(option);
            }
        );
    }
);

$(window).on('resize', resize);

// Resize function
function resize() {
setTimeout(function () {
    // Resize chart
    myChart.resize();
}, 200);
}
