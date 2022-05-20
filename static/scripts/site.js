var Site = function() {
    //	this.symbol = "PETR4.SA";
};

Site.prototype.Init = function() {
    // store the site context.
    var that = this;

    that.LoadStoredSymbols(true);
    jQuery("#symbol").on("click", function() {
        jQuery(this).val("");
    });

    jQuery('#modalAlertRemoveSymbol').on('show.bs.modal', function(event) {
        var button = jQuery(event.relatedTarget); // Button that triggered the modal
        var symbol = button.data('id'); // Extract info from data-* attributes
        var shortName = button.data('shortname'); // Extract info from data-* attributes
        // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
        // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
        var modal = jQuery(this);
        modal.find('.btn-remove').attr('data-id', symbol);
        modal.find('.modal-body .symbolName').html(' ' + shortName);
    });

    jQuery('.btn-remove').on("click", function() {
        that.RemoveSymbol(jQuery(this).attr("data-id"));
        jQuery('#modalAlertRemoveSymbol').modal('hide');
    });
};

Site.prototype.LoadStoredSymbols = function(reloadChart = false) {

    // store the site context.
    var that = this;

    // pull the HTTP Request
    $.ajax({
        url: "/list",
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {
            var symbolList = "";

            for (var i = 0, l = Object.keys(data).length; i < l; i++) {
                symbolList += '<li><span class="getSymbol" onclick="site.getSymbolChart(this)" data-id="' + data[i].sym + '">' + data[i].shortName + '</span><span data-toggle="modal" data-id="' + data[i].sym + '" data-shortname="' + data[i].shortName + '" data-target="#modalAlertRemoveSymbol" class="removeItem">x</span></li>';
            }

            jQuery("ul.symbolList").html(symbolList);

            var context = {};

            context.shortName = data[0].shortName;
            context.symbol = data[0].sym;
            that.symbol = data[0].sym;

            // call the request to load the chart and pass the data context with it.
            if (reloadChart)
                that.LoadChart(context);
        } else {
            jQuery("#chart_container").html("");
            jQuery(".symbolListDiv").hide("");
        }
    });
}

Site.prototype.RemoveSymbol = function(symbolId) {

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/remove?symbol=" + symbolId,
        method: "GET",
        cache: false
    }).done(function(data) {
        //            jQuery( "ul.symbolList" ).html(symbolList);

        var context = {};

        context.removed = data.removed;
        context.message = data.message;

        // call the request to a message with result
        //            that.ShowMessage(context);
        that.LoadStoredSymbols(true);
    });
}

Site.prototype.exponentialMovingAverage = function(data, sma, window = 5, last = false) {

    var dates = Object.keys(data);
    var prices = Object.values(data);

    if (!prices || prices.length < window) {
        return [];
    }

    let index = window - 1;
    let previousEmaIndex = 0;
    const length = prices.length;
    const smoothingFactor = 2 / (window + 1);

    exponentialMovingAverages = sma;
    exponentialMovingAveragesWithDates = [];

    while (++index < length) {
        const value = prices[index];
        const previousEma = exponentialMovingAverages[previousEmaIndex++][1];
        const currentEma = (value - previousEma) * smoothingFactor + previousEma;
        exponentialMovingAverages.push(currentEma);
        exponentialMovingAveragesWithDates.push([parseInt(dates[index]), currentEma])
    }

    return exponentialMovingAveragesWithDates;
}

Site.prototype.simpleMovingAverage = function(data, window = 5, last = false) {

    // console.log(Object.keys(prices));

    var dates = Object.keys(data);
    var prices = Object.values(data);

    if (!prices || prices.length < window) {
        return [];
    }

    let index = window - 1;
    const length = prices.length + 1;

    const simpleMovingAverages = {};

    while (++index < length) {
        const windowPriceSlice = prices.slice(index - window, index);
        const windowDateSlice = dates.slice(index - window, index);
        const sum = windowPriceSlice.reduce((prev, curr) => prev + curr, 0);
        simpleMovingAverages[parseInt(windowDateSlice.slice(-1))] = sum / window;
    }

    if (last == true)
        return simpleMovingAverages[Object.keys(simpleMovingAverages)[Object.keys(simpleMovingAverages).length - 1]]

    return simpleMovingAverages;
}

// https://www.highcharts.com/forum/viewtopic.php?t=41321#p144259
Site.prototype.checkLineIntersection = function(a1, a2) {
    if (a1 && a2) {
        var saX = a2.x - a1.x,
            saY = a2.high - a1.high,
            sbY = a2.low - a1.low,
            sabX = a1.plotX - a2.plotX,
            sabY = a1.high - a1.low,
            u,
            t;


        u = (-saY * sabX + saX * sabY) / (-saX * saY + saX * sbY);
        t = (saX * sabY - sbY * sabX) / (-saX * saY + saX * sbY);

        if (u >= 0 && u <= 1 && t >= 0 && t <= 1) {
            return {
                plotX: a1.x + (t * saX),
                plotY: a1.high + (t * saY)
            };
        }
    }

    return false;
}

Site.prototype.GetQuote = function(symbol = this.symbol) {

    jQuery(".symbolListDiv .loadingChart").addClass("d-inline-block");

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/get?symbol=" + symbol,
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {
            var symbolList = "";

            for (var i = 0, l = Object.keys(data).length; i < l; i++) {
                symbolList += '<li>' + data[i].shortName + '<span data-toggle="modal" data-id="' + data[i].sym + '" data-shortname="' + data[i].shortName + '" data-target="#modalAlertRemoveSymbol" class="removeItem">x</span></li>';
            }

            jQuery( "ul.symbolList" ).html(symbolList);

            var context = {};

            context.shortName = data.shortName;
            context.symbol = data.sym;
            that.symbol = data.sym;

            // call the request to load the chart and pass the data context with it.
            that.LoadChart(context);
            //            jQuery( ".symbolListDiv" ).show();
        }
        //		// set up a data context for just what we need.
        //		var context = {};
        //		context.shortName = data.shortName;
        //		context.symbol = data.sym;
        ////		context.price = data.ask;
        //
        ////		if(data.quoteType="MUTUALFUND"){
        ////			context.price = data.previousClose
        ////		}
        //
        //		// call the request to load the chart and pass the data context with it.
        //		that.LoadChart(context);
    });
};

Site.prototype.SubmitForm = function() {
    this.symbol = $("#symbol").val();
    this.GetQuote();
}

Site.prototype.getSymbolChart = function(e) {
    symbol = jQuery(e).attr("data-id");
    this.symbol = symbol;
    this.GetQuote(symbol);
}

Site.prototype.LoadChart = function(quote) {

    var that = this;
    $.ajax({
        //		url: "/historydb?symbol=" + that.symbol,
        url: "/indicators?symbol=" + that.symbol,
        method: "GET",
        cache: false
    }).done(function(data) {

        that.RenderChart(data, quote);

        var lastElementData = data[Object.keys(data)[Object.keys(data).length - 1]]
        that.RenderIndicators(lastElementData);

        that.LoadStoredSymbols(false);
        //        console.log(simpleMovingAverageArray50);
    });
};

//Site.prototype.RenderIndicators = function(data) {
//    console.log(Object.keys(data).length);
//
//    if (Object.keys(data).length > 0) {
//
//        //                                "$macd_indicator.weight",
//        //                                "$cmo_9_indicator.weight",
//        //                                "$ema_10_indicator.weight",
//        //                                "$ema_20_indicator.weight",
//        //                                "$ema_50_indicator.weight",
//        //                                "$ema_100_indicator.weight",
//        //                                "$rsi_indicator.weight",
//        //                                "$rsi_stoch_indicator.weight",
//        var indicators_tendency = [];
//        var indicators = [];
//
//        indicators_tendency["up"] = data.indicators_up
//        indicators_tendency["down"] = data.indicators_down
//        indicators_tendency["neutral"] = data.indicators_neutral
//        indicators_tendency["recommendation"] = ""
//
//        switch(data.indicators_recommendation){
//            case "Strong Buy":
//                indicators_tendency["recommendation"] = "Tendência de Alta Forte";
//                break;
//
//            case "Buy":
//                indicators_tendency["recommendation"] = "Tendência de Alta";
//                break;
//
//            case "Neutral":
//                indicators_tendency["recommendation"] = "Tendência Neutra";
//                break;
//
//            case "Sell":
//                indicators_tendency["recommendation"] = "Tendência de Baixa";
//                break;
//
//            case "Strong Sell":
//                indicators_tendency["recommendation"] = "Tendência de Baixa Forte";
//                break;
//        }
//
//
//        var macd_indicator = [];
//        macd_indicator["name"] = "Nível MACD (12, 26)";
//        macd_indicator["value"] = data.macdSignal;
//        macd_indicator["recommendation"] = data.macd_indicator.recommendation;
//        indicators.push(macd_indicator);
//
//        var cmo_9_indicator = [];
//        cmo_9_indicator["name"] = "Oscilador de Momento de Chande (9)";
//        cmo_9_indicator["value"] = data.cmo_9;
//        cmo_9_indicator["recommendation"] = data.cmo_9_indicator.recommendation;
//        indicators.push(cmo_9_indicator);
//
//        var ema_10_indicator = [];
//        ema_10_indicator["name"] = "Média Móvel Exponencial (10)";
//        ema_10_indicator["value"] = data.ema_10;
//        ema_10_indicator["recommendation"] = data.ema_10_indicator.recommendation;
//        indicators.push(ema_10_indicator);
//
//        var ema_20_indicator = [];
//        ema_20_indicator["name"] = "Média Móvel Exponencial (20)";
//        ema_20_indicator["value"] = data.ema_20;
//        ema_20_indicator["recommendation"] = data.ema_20_indicator.recommendation;
//        indicators.push(ema_20_indicator);
//
//        var ema_50_indicator = [];
//        ema_50_indicator["name"] = "Média Móvel Exponencial (50)";
//        ema_50_indicator["value"] = data.ema_50;
//        ema_50_indicator["recommendation"] = data.ema_50_indicator.recommendation;
//        indicators.push(ema_50_indicator);
//
//        var ema_100_indicator = [];
//        ema_100_indicator["name"] = "Média Móvel Exponencial (100)";
//        ema_100_indicator["value"] = data.ema_100;
//        ema_100_indicator["recommendation"] = data.ema_100_indicator.recommendation;
//        indicators.push(ema_100_indicator);
//
//        var rsi_indicator = [];
//        rsi_indicator["name"] = "Índice de Força Relativa (14)";
//        rsi_indicator["value"] = data.rsi;
//        rsi_indicator["recommendation"] = data.rsi_indicator.recommendation;
//        indicators.push(rsi_indicator);
//
//        var rsi_stoch_indicator = [];
//        rsi_stoch_indicator["name"] = "IFR Estocástico";
//        rsi_stoch_indicator["value"] = data.rsi_stoch;
//        rsi_stoch_indicator["recommendation"] = data.rsi_stoch_indicator.recommendation;
//        indicators.push(rsi_stoch_indicator);
//
//        //        indicators.push([])
//        //                    <tr>
//        //                      <th scope="row">1</th>
//        //                      <td>Mark</td>
//        //                      <td>Otto</td>
//        //                      <td class="indicator-action">@mdo</td>
//        //                    </tr>
//        var indicators_table = '<table class="table table-dark">';
//            indicators_table += '<thead class="thead-light">';
//            indicators_table += '<tr>';
//            indicators_table += '<th scope="col">#</th>';
//            indicators_table += '<th scope="col">Nome</th>';
//            indicators_table += '<th scope="col">Valor</th>';
//            indicators_table += '<th scope="col">Ação</th>';
//            indicators_table += '</tr>';
//            indicators_table += '</thead>';
//            indicators_table += '<tbody>';
//
//        var i_indicator = 0;
//        var indicator_row = "";
//        indicators.forEach(function logArrayElements(element, index, array) {
//            i_indicator++;
//            console.log("a[" + index + "] = " + element);
//            indicator_row += '<tr>';
//            indicator_row += '<th scope="row">' + i_indicator + '</th>';
//            indicator_row += '<th>' + element["name"] + '</th>';
//            indicator_row += '<th>' + element["value"] + '</th>';
//            indicator_row += '<th class="indicator-action">' + element["recommendation"] + '</th>';
//            indicator_row += '</tr>';
//            indicators_table += indicator_row;
//        })
//        indicators_table += '</tbody>';
//        indicators_table += '</table>';
//
//        console.log(indicators_table)
////        for (var i = 0, l = Object.keys(data).length; i < l; i++) {
////
////        }
//        //        data[i].sym
//
//        jQuery("#indicators").html(indicators_table);
//
////        var context = {};
////
////        context.shortName = data[0].shortName;
////        context.symbol = data[0].sym;
////        that.symbol = data[0].sym;
////
////        // call the request to load the chart and pass the data context with it.
////        if (reloadChart)
////            that.LoadChart(context);
//    } else {
//        jQuery("#chart_container").html("");
//        jQuery(".symbolListDiv").hide("");
//    }
//}

Site.prototype.RenderChart = function(data, quote) {
    var priceData = [];
    var volumeData = [];

    var title = quote.shortName + " (" + quote.symbol + ")";

    jQuery("h4.currentSymbolName").text(title);
    console.log(data[0]._id.Datetime)
    // Map your data to desired format
    var closeData = data.map(o => ([o._id.Datetime, o.price]));
    var volumeData = data.map(o => ([o._id.Datetime, o.volume]));
    //        var series = data.map(o => ({x: data._id.Datetime, data: [{y: data.price}]}));
    //                       json.map(o => ({name: o.name, data: [{y: Number(o.Salary)}]}));

    //        console.log(close)

    // Close and Volume data
    //        for(var i in data.Close){
    //            var volume = data.Volume[i];
    //            var close = data.Close[i];
    //
    //            var dt = parseInt(i);
    //
    //            if(close != null){
    //                priceData.push([dt, close]);
    //            }
    //
    //            if(volume != null){
    //                volumeData.push([dt, volume])
    //            }
    //
    //        }

    console.log(volumeData);

    this.chart = Highcharts.stockChart('chart_container', {
        time: {
            timezone: 'Etc/GMT-1'
        },
        yAxis: [{
            labels: {
                align: 'left'
            },
            height: '60%',
            resize: {
                enabled: true
            }
        }, {
            labels: {
                align: 'left'
            },
            top: '60%',
            height: '20%',
            offset: 0
        }, {
            labels: {
                align: 'left'
            },
            top: '90%',
            height: '10%',
            offset: 0
        }],

        credits: {
            enabled: false
        },
        //
        //            title: {
        //                text: title
        //            },
        plotOptions: {
            series: {
                dataGrouping: {
                    enabled: false
                }
            }
        },
        series: [{
                name: quote.shortName,
                data: closeData,
                id: quote.shortName + '-price',
                tooltip: {
                    valueDecimals: 2
                }
            }, {
                yAxis: 1,
                type: 'macd',
                linkedTo: quote.shortName + '-price',
                params: {
                    shortPeriod: 12,
                    longPeriod: 26,
                    signalPeriod: 9,
                    period: 26
                }
            },
            {
                type: 'column',
                id: quote.shortName + '-volume',
                name: quote.shortName + ' Volume',
                data: volumeData,
                yAxis: 2
            }
        ],

        rangeSelector: {
            buttons: [{
                    type: 'minute',
                    count: 15,
                    text: '15m'
                }, {
                    type: 'minute',
                    count: 30,
                    text: '30m'
                }, {
                    type: 'hour',
                    count: 1,
                    text: '1h'
                },
                {
                    type: 'hour',
                    count: 3,
                    text: '3h'
                }, {
                    type: 'hour',
                    count: 6,
                    text: '6h'
                }, {
                    type: 'hour',
                    count: 12,
                    text: '1h'
                }, {
                    type: 'day',
                    count: 1,
                    text: '1d'
                }, {
                    type: 'day',
                    count: 3,
                    text: '3d'
                }, {
                    type: 'day',
                    count: 7,
                    text: '7d'
                }, {
                    type: 'all',
                    count: 1,
                    text: 'Tudo'
                }
            ],
            selected: 3,
            inputEnabled: false
        },

        responsive: {
            rules: [{
                condition: {
                    maxWidth: 800
                },
                chartOptions: {
                    rangeSelector: {
                        inputEnabled: false
                    }
                }
            }]
        }

    });

    jQuery(".symbolListDiv").show();
    jQuery(".symbolListDiv .loadingChart").removeClass('d-inline-block');
    jQuery("#navbarToggleExternalContent").collapse('hide');
};

var site = new Site();

jQuery(document).ready(() => {
    site.Init();
});

var Site = function() {
    //	this.symbol = "PETR4.SA";
};

Site.prototype.Init = function() {
    // store the site context.
    var that = this;

    that.LoadStoredSymbols(true);
    jQuery("#symbol").on("click", function() {
        jQuery(this).val("");
    });

    jQuery('#modalAlertRemoveSymbol').on('show.bs.modal', function(event) {
        var button = jQuery(event.relatedTarget); // Button that triggered the modal
        var symbol = button.data('id'); // Extract info from data-* attributes
        var shortName = button.data('shortname'); // Extract info from data-* attributes
        // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
        // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
        var modal = jQuery(this);
        modal.find('.btn-remove').attr('data-id', symbol);
        modal.find('.modal-body .symbolName').html(' ' + shortName);
    });

    jQuery('.btn-remove').on("click", function() {
        that.RemoveSymbol(jQuery(this).attr("data-id"));
        jQuery('#modalAlertRemoveSymbol').modal('hide');
    });
};

Site.prototype.LoadStoredSymbols = function(reloadChart = false) {

    // store the site context.
    var that = this;

    // pull the HTTP Request
    $.ajax({
        url: "/list",
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {
            var symbolList = "";

            for (var i = 0, l = Object.keys(data).length; i < l; i++) {
                symbolList += '<li><span class="getSymbol" onclick="site.getSymbolChart(this)" data-id="' + data[i].sym + '">' + data[i].shortName + '</span><span data-toggle="modal" data-id="' + data[i].sym + '" data-shortname="' + data[i].shortName + '" data-target="#modalAlertRemoveSymbol" class="removeItem">x</span></li>';
            }

            jQuery("ul.symbolList").html(symbolList);

            var context = {};

            context.shortName = data[0].shortName;
            context.symbol = data[0].sym;
            that.symbol = data[0].sym;

            // call the request to load the chart and pass the data context with it.
            if (reloadChart)
                that.LoadChart(context);
        } else {
            jQuery("#chart_container").html("");
            jQuery(".symbolListDiv").hide("");
        }
    });
}

Site.prototype.RemoveSymbol = function(symbolId) {

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/remove?symbol=" + symbolId,
        method: "GET",
        cache: false
    }).done(function(data) {
        //            jQuery( "ul.symbolList" ).html(symbolList);

        var context = {};

        context.removed = data.removed;
        context.message = data.message;

        // call the request to a message with result
        //            that.ShowMessage(context);
        that.LoadStoredSymbols(true);
    });
}

Site.prototype.exponentialMovingAverage = function(data, sma, window = 5, last = false) {

    var dates = Object.keys(data);
    var prices = Object.values(data);

    if (!prices || prices.length < window) {
        return [];
    }

    let index = window - 1;
    let previousEmaIndex = 0;
    const length = prices.length;
    const smoothingFactor = 2 / (window + 1);

    exponentialMovingAverages = sma;
    exponentialMovingAveragesWithDates = [];

    while (++index < length) {
        const value = prices[index];
        const previousEma = exponentialMovingAverages[previousEmaIndex++][1];
        const currentEma = (value - previousEma) * smoothingFactor + previousEma;
        exponentialMovingAverages.push(currentEma);
        exponentialMovingAveragesWithDates.push([parseInt(dates[index]), currentEma])
    }

    return exponentialMovingAveragesWithDates;
}

Site.prototype.simpleMovingAverage = function(data, window = 5, last = false) {

    // console.log(Object.keys(prices));

    var dates = Object.keys(data);
    var prices = Object.values(data);

    if (!prices || prices.length < window) {
        return [];
    }

    let index = window - 1;
    const length = prices.length + 1;

    const simpleMovingAverages = {};

    while (++index < length) {
        const windowPriceSlice = prices.slice(index - window, index);
        const windowDateSlice = dates.slice(index - window, index);
        const sum = windowPriceSlice.reduce((prev, curr) => prev + curr, 0);
        simpleMovingAverages[parseInt(windowDateSlice.slice(-1))] = sum / window;
    }

    if (last == true)
        return simpleMovingAverages[Object.keys(simpleMovingAverages)[Object.keys(simpleMovingAverages).length - 1]]

    return simpleMovingAverages;
}

// https://www.highcharts.com/forum/viewtopic.php?t=41321#p144259
Site.prototype.checkLineIntersection = function(a1, a2) {
    if (a1 && a2) {
        var saX = a2.x - a1.x,
            saY = a2.high - a1.high,
            sbY = a2.low - a1.low,
            sabX = a1.plotX - a2.plotX,
            sabY = a1.high - a1.low,
            u,
            t;


        u = (-saY * sabX + saX * sabY) / (-saX * saY + saX * sbY);
        t = (saX * sabY - sbY * sabX) / (-saX * saY + saX * sbY);

        if (u >= 0 && u <= 1 && t >= 0 && t <= 1) {
            return {
                plotX: a1.x + (t * saX),
                plotY: a1.high + (t * saY)
            };
        }
    }

    return false;
}

//Site.prototype.GetQuote = function(symbol = this.symbol){
//	// store the site context.
//    //	var that = this;
//
//	// pull the HTTP REquest
//	$.ajax({
//		url: "/quote?symbol=" + symbol,
//		method: "GET",
//		cache: false
//	}).done(function(data) {
//
//		// set up a data context for just what we need.
//		var context = {};
//		context.shortName = data.shortName;
//		context.symbol = data.sym;
////		context.price = data.ask;
//
////		if(data.quoteType="MUTUALFUND"){
////			context.price = data.previousClose
////		}
//
//		// call the request to load the chart and pass the data context with it.
//		that.LoadChart(context);
//	});
//};
Site.prototype.GetQuote = function(symbol = this.symbol) {

    jQuery(".symbolListDiv .loadingChart").addClass("d-inline-block");

    // store the site context.
    var that = this;

    // pull the HTTP REquest
    $.ajax({
        url: "/get?symbol=" + symbol,
        method: "GET",
        cache: false
    }).done(function(data) {

        var data = JSON.parse(data);
        if (Object.keys(data).length > 0) {
            //            var symbolList = "";

            //            for (var i = 0, l = Object.keys(data).length; i < l; i++) {
            //                symbolList += '<li>' + data[i].shortName + '<span data-toggle="modal" data-id="' + data[i].sym + '" data-shortname="' + data[i].shortName + '" data-target="#modalAlertRemoveSymbol" class="removeItem">x</span></li>';
            //            }

            //            jQuery( "ul.symbolList" ).html(symbolList);

            var context = {};

            context.shortName = data.shortName;
            context.symbol = data.sym;
            that.symbol = data.sym;

            // call the request to load the chart and pass the data context with it.
            that.LoadChart(context);
            //            jQuery( ".symbolListDiv" ).show();
        }
        //		// set up a data context for just what we need.
        //		var context = {};
        //		context.shortName = data.shortName;
        //		context.symbol = data.sym;
        ////		context.price = data.ask;
        //
        ////		if(data.quoteType="MUTUALFUND"){
        ////			context.price = data.previousClose
        ////		}
        //
        //		// call the request to load the chart and pass the data context with it.
        //		that.LoadChart(context);
    });
};

Site.prototype.SubmitForm = function() {
    this.symbol = $("#symbol").val();
    this.GetQuote();
}

Site.prototype.getSymbolChart = function(e) {
    symbol = jQuery(e).attr("data-id");
    this.symbol = symbol;
    this.GetQuote(symbol);
}

Site.prototype.LoadChart = function(quote) {

    var that = this;
    $.ajax({
        //		url: "/historydb?symbol=" + that.symbol,
        url: "/indicators?symbol=" + that.symbol,
        method: "GET",
        cache: false
    }).done(function(data) {

        //		console.log('Média Movel Simples (10)', that.simpleMovingAverage(parsedDataClose, 10, true));
        //		console.log('Média Movel Simples (20)', that.simpleMovingAverage(JSON.parse(data).Close, 20, true));
        //		console.log('Média Movel Simples (30)', that.simpleMovingAverage(JSON.parse(data).Close, 30, true));
        //		console.log('Média Movel Simples (40)', that.simpleMovingAverage(JSON.parse(data).Close, 40, true));
        //		console.log('Média Movel Simples (50)', that.simpleMovingAverage(JSON.parse(data).Close, 50, true));
        //		console.log('Média Movel Simples (100)', that.simpleMovingAverage(JSON.parse(data).Close, 100, true));
        //		console.log('Média Movel Simples (200)', that.simpleMovingAverage(JSON.parse(data).Close, 200, true));
        //		that.RenderChart(JSON.parse(data), quote);
        that.RenderChart(data, quote);
        var lastElementData = data[Object.keys(data)[Object.keys(data).length - 1]]
        that.RenderIndicators(lastElementData);
        //
        //		sma50 = [];
        //		Object.entries(that.simpleMovingAverage(JSON.parse(data).Close, 50, false)).forEach(([key, value]) => {
        //            sma50.push([parseInt(key), value]);
        //        });
        //        sma100 = [];
        //		Object.entries(that.simpleMovingAverage(JSON.parse(data).Close, 100, false)).forEach(([key, value]) => {
        //            sma100.push([parseInt(key), value]);
        //        });
        //        sma200 = [];
        //		Object.entries(that.simpleMovingAverage(JSON.parse(data).Close, 200, false)).forEach(([key, value]) => {
        //            sma200.push([parseInt(key), value]);
        //        });
        //
        //        ema50 = that.exponentialMovingAverage(JSON.parse(data).Close, sma50.slice(), 50, false);
        //        ema100 = that.exponentialMovingAverage(JSON.parse(data).Close, sma100.slice(), 100, false);
        //        ema200 = that.exponentialMovingAverage(JSON.parse(data).Close, sma200.slice(), 200, false);
        //
        //
        //
        //        console.log(sma50);
        //        console.log(ema50);

        //		that.chart.addSeries({
        //		    id:   'sma50',
        //            name: 'Média Movel Simples (50)',
        //            data:  sma50
        //        });
        //		that.chart.addSeries({
        //		    id:   'sma100',
        //            name: 'Média Movel Simples (100)',
        //            data:  sma100
        //        });
        //		that.chart.addSeries({
        //		    id:   'sma200',
        //            name: 'Média Movel Simples (200)',
        //            data:  sma200
        //        });

        //        that.chart.addSeries({
        //		    id:   'ema50',
        //            name: 'Média Movel Exponencial (50)',
        //            data:  ema50
        //        });
        //
        //        that.chart.addSeries({
        //		    id:   'ema100',
        //            name: 'Média Movel Exponencial (100)',
        //            data:  ema100
        //        });
        //
        //        that.chart.addSeries({
        //		    id:   'ema200',
        //            name: 'Média Movel Exponencial (200)',
        //            data:  ema200
        //        });

        console.log(series = that.chart.series)
        that.LoadStoredSymbols(false);
        //        console.log(simpleMovingAverageArray50);
    });
};

Site.prototype.RenderIndicators = function(data) {
    if (Object.keys(data).length > 0) {

        //                                "$macd_indicator.weight",
        //                                "$cmo_9_indicator.weight",
        //                                "$ema_10_indicator.weight",
        //                                "$ema_20_indicator.weight",
        //                                "$ema_50_indicator.weight",
        //                                "$ema_100_indicator.weight",
        //                                "$rsi_indicator.weight",
        //                                "$rsi_stoch_indicator.weight",
//        var indicators = [];
//
//        var macd_indicator = [];
//        macd_indicator["name"] = "Nível MACD (12, 26)";
//        macd_indicator["value"] = data.macdSignal;
//        macd_indicator["recommendation"] = data.macd_indicator.recommendation;
//        indicators.push(macd_indicator);
//
//        var cmo_9_indicator = [];
//        cmo_9_indicator["name"] = "Oscilador de Momento de Chande (9)";
//        cmo_9_indicator["value"] = data.cmo_9;
//        cmo_9_indicator["recommendation"] = data.cmo_9_indicator.recommendation;
//        indicators.push(cmo_9_indicator);
//
//        var ema_10_indicator = [];
//        ema_10_indicator["name"] = "Média Móvel Exponencial (10)";
//        ema_10_indicator["value"] = data.ema_10;
//        ema_10_indicator["recommendation"] = data.ema_10_indicator.recommendation;
//        indicators.push(ema_10_indicator);
//
//        var ema_20_indicator = [];
//        ema_20_indicator["name"] = "Média Móvel Exponencial (20)";
//        ema_20_indicator["value"] = data.ema_20;
//        ema_20_indicator["recommendation"] = data.ema_20_indicator.recommendation;
//        indicators.push(ema_20_indicator);
//
//        var ema_50_indicator = [];
//        ema_50_indicator["name"] = "Média Móvel Exponencial (50)";
//        ema_50_indicator["value"] = data.ema_50;
//        ema_50_indicator["recommendation"] = data.ema_50_indicator.recommendation;
//        indicators.push(ema_50_indicator);
//
//        var ema_100_indicator = [];
//        ema_100_indicator["name"] = "Média Móvel Exponencial (100)";
//        ema_100_indicator["value"] = data.ema_100;
//        ema_100_indicator["recommendation"] = data.ema_100_indicator.recommendation;
//        indicators.push(ema_100_indicator);
//
//        var rsi_indicator = [];
//        rsi_indicator["name"] = "Índice de Força Relativa (14)";
//        rsi_indicator["value"] = data.rsi;
//        rsi_indicator["recommendation"] = data.rsi_indicator.recommendation;
//        indicators.push(rsi_indicator);
//
//        var rsi_stoch_indicator = [];
//        rsi_stoch_indicator["name"] = "IFR Estocástico";
//        rsi_stoch_indicator["value"] = data.rsi_stoch;
//        rsi_stoch_indicator["recommendation"] = data.rsi_stoch_indicator.recommendation;
//        indicators.push(rsi_stoch_indicator);

        var indicators_tendency = [];
        var indicators = [];

        indicators_tendency["up"] = data.indicators_up
        indicators_tendency["down"] = data.indicators_down
        indicators_tendency["neutral"] = data.indicators_neutral
        indicators_tendency["recommendation"] = ""

        switch(data.indicators_recommendation){
            case "Strong Buy":
                indicators_tendency["recommendation"] = "Tendência de Alta Forte";
                break;

            case "Buy":
                indicators_tendency["recommendation"] = "Tendência de Alta";
                break;

            case "Neutral":
                indicators_tendency["recommendation"] = "Tendência Neutra";
                break;

            case "Sell":
                indicators_tendency["recommendation"] = "Tendência de Baixa";
                break;

            case "Strong Sell":
                indicators_tendency["recommendation"] = "Tendência de Baixa Forte";
                break;
        }


        var macd_indicator = [];
        macd_indicator["name"] = "Nível MACD (12, 26)";
        macd_indicator["value"] = data.macdSignal;
        macd_indicator["recommendation"] = data.macd_indicator.recommendation;
        indicators.push(macd_indicator);

        var cmo_9_indicator = [];
        cmo_9_indicator["name"] = "Oscilador de Momento de Chande (9)";
        cmo_9_indicator["value"] = data.cmo_9;
        cmo_9_indicator["recommendation"] = data.cmo_9_indicator.recommendation;
        indicators.push(cmo_9_indicator);

        var ema_10_indicator = [];
        ema_10_indicator["name"] = "Média Móvel Exponencial (10)";
        ema_10_indicator["value"] = data.ema_10;
        ema_10_indicator["recommendation"] = data.ema_10_indicator.recommendation;
        indicators.push(ema_10_indicator);

        var ema_20_indicator = [];
        ema_20_indicator["name"] = "Média Móvel Exponencial (20)";
        ema_20_indicator["value"] = data.ema_20;
        ema_20_indicator["recommendation"] = data.ema_20_indicator.recommendation;
        indicators.push(ema_20_indicator);

        var ema_50_indicator = [];
        ema_50_indicator["name"] = "Média Móvel Exponencial (50)";
        ema_50_indicator["value"] = data.ema_50;
        ema_50_indicator["recommendation"] = data.ema_50_indicator.recommendation;
        indicators.push(ema_50_indicator);

        var ema_100_indicator = [];
        ema_100_indicator["name"] = "Média Móvel Exponencial (100)";
        ema_100_indicator["value"] = data.ema_100;
        ema_100_indicator["recommendation"] = data.ema_100_indicator.recommendation;
        indicators.push(ema_100_indicator);

        var rsi_indicator = [];
        rsi_indicator["name"] = "Índice de Força Relativa (14)";
        rsi_indicator["value"] = data.rsi;
        rsi_indicator["recommendation"] = data.rsi_indicator.recommendation;
        indicators.push(rsi_indicator);

        var rsi_stoch_indicator = [];
        rsi_stoch_indicator["name"] = "IFR Estocástico";
        rsi_stoch_indicator["value"] = data.rsi_stoch;
        rsi_stoch_indicator["recommendation"] = data.rsi_stoch_indicator.recommendation;
        indicators.push(rsi_stoch_indicator);

        //        indicators.push([])
        //                    <tr>
        //                      <th scope="row">1</th>
        //                      <td>Mark</td>
        //                      <td>Otto</td>
        //                      <td class="indicator-action">@mdo</td>
        //                    </tr>
        var indicators_table = '<table class="table table-dark">';
            indicators_table += '<thead class="thead-light">';
            indicators_table += '<tr>';
            indicators_table += '<th scope="col">#</th>';
            indicators_table += '<th scope="col">Nome</th>';
            indicators_table += '<th scope="col">Valor</th>';
            indicators_table += '<th scope="col">Ação</th>';
            indicators_table += '</tr>';
            indicators_table += '</thead>';
            indicators_table += '<tbody>';

        var i_indicator = 0;
        var indicator_row = "";

        indicators.forEach(function logArrayElements(element, index, array) {
            i_indicator++;
            indicator_row = "";
            console.log(element["name"]);
            indicator_row += '<tr>';
            indicator_row += '<th scope="row">' + i_indicator + '</th>';
            indicator_row += '<th>' + element["name"] + '</th>';
            indicator_row += '<th>' + Math.round(element["value"] * 100) / 100 + '</th>';
            indicator_row += '<th class="indicator-action">' + element["recommendation"]+ '</th>';
            indicator_row += '</tr>';
            indicators_table += indicator_row;
        })
        indicators_table += '</tbody>';
        indicators_table += '</table>';

        console.log(indicators_table)
//        for (var i = 0, l = Object.keys(data).length; i < l; i++) {
//
//        }
        //        data[i].sym

        jQuery("#indicators").html(indicators_table);


        console.log(indicators)

        //        indicators.push([])
        //                    <tr>
        //                      <th scope="row">1</th>
        //                      <td>Mark</td>
        //                      <td>Otto</td>
        //                      <td class="indicator-action">@mdo</td>
        //                    </tr>

//        for (var i = 0, l = Object.keys(data).length; i < l; i++) {
//            symbolList += '<tr></tr>';
//        }
        //        data[i].sym

//        jQuery("ul.symbolList").html(symbolList);

//        var context = {};
//
//        context.shortName = data[0].shortName;
//        context.symbol = data[0].sym;
//        that.symbol = data[0].sym;

//        // call the request to load the chart and pass the data context with it.
//        if (reloadChart)
//            that.LoadChart(context);
    } else {
        jQuery("#chart_container").html("");
        jQuery(".symbolListDiv").hide("");
    }
}

Site.prototype.RenderChart = function(data, quote) {
    var priceData = [];
    var volumeData = [];

    var title = quote.shortName + " (" + quote.symbol + ")";

    jQuery("h4.currentSymbolName").text(title);
    console.log(data[0]._id.Datetime)
    // Map your data to desired format
    var closeData = data.map(o => ([o._id.Datetime, o.price]));
    var volumeData = data.map(o => ([o._id.Datetime, o.volume]));
    //        var series = data.map(o => ({x: data._id.Datetime, data: [{y: data.price}]}));
    //                       json.map(o => ({name: o.name, data: [{y: Number(o.Salary)}]}));

    //        console.log(close)

    // Close and Volume data
    //        for(var i in data.Close){
    //            var volume = data.Volume[i];
    //            var close = data.Close[i];
    //
    //            var dt = parseInt(i);
    //
    //            if(close != null){
    //                priceData.push([dt, close]);
    //            }
    //
    //            if(volume != null){
    //                volumeData.push([dt, volume])
    //            }
    //
    //        }

    console.log(volumeData);

    this.chart = Highcharts.stockChart('chart_container', {
        time: {
            timezone: 'Etc/GMT-1'
        },
        yAxis: [{
            labels: {
                align: 'left'
            },
            height: '60%',
            resize: {
                enabled: true
            }
        }, {
            labels: {
                align: 'left'
            },
            top: '60%',
            height: '20%',
            offset: 0
        }, {
            labels: {
                align: 'left'
            },
            top: '90%',
            height: '10%',
            offset: 0
        }],

        credits: {
            enabled: false
        },
        //
        //            title: {
        //                text: title
        //            },
        plotOptions: {
            series: {
                dataGrouping: {
                    enabled: false
                }
            }
        },
        series: [{
                name: quote.shortName,
                data: closeData,
                id: quote.shortName + '-price',
                tooltip: {
                    valueDecimals: 2
                }
            }, {
                yAxis: 1,
                type: 'macd',
                linkedTo: quote.shortName + '-price',
                params: {
                    shortPeriod: 12,
                    longPeriod: 26,
                    signalPeriod: 9,
                    period: 26
                }
            },
            {
                type: 'column',
                id: quote.shortName + '-volume',
                name: quote.shortName + ' Volume',
                data: volumeData,
                yAxis: 2
            }
        ],

        rangeSelector: {
            buttons: [{
                    type: 'minute',
                    count: 15,
                    text: '15m'
                }, {
                    type: 'minute',
                    count: 30,
                    text: '30m'
                }, {
                    type: 'hour',
                    count: 1,
                    text: '1h'
                },
                {
                    type: 'hour',
                    count: 3,
                    text: '3h'
                }, {
                    type: 'hour',
                    count: 6,
                    text: '6h'
                }, {
                    type: 'hour',
                    count: 12,
                    text: '1h'
                }, {
                    type: 'day',
                    count: 1,
                    text: '1d'
                }, {
                    type: 'day',
                    count: 3,
                    text: '3d'
                }, {
                    type: 'day',
                    count: 7,
                    text: '7d'
                }, {
                    type: 'all',
                    count: 1,
                    text: 'Tudo'
                }
            ],
            selected: 3,
            inputEnabled: false
        },

        responsive: {
            rules: [{
                condition: {
                    maxWidth: 800
                },
                chartOptions: {
                    rangeSelector: {
                        inputEnabled: false
                    }
                }
            }]
        }

    });

    jQuery(".symbolListDiv").show();
    jQuery(".symbolListDiv .loadingChart").removeClass('d-inline-block');
    jQuery("#navbarToggleExternalContent").collapse('hide');
};

var site = new Site();

jQuery(document).ready(() => {
    site.Init();
})