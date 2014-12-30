document.addEventListener("DOMContentLoaded", function() {
    renderInfo();
    renderTotalVsLikes();
    renderTfidf();
});

function addAnalysis(title, el) {
    var container = document.querySelector("#container")
    var subTitle = document.createElement("h2");
    subTitle.innerHTML = title;
    container.appendChild(subTitle);
    container.appendChild(el);
}

function renderInfo() {
    d3.json("group.json", function(err, data) {
        if (err != null) {
            throw new Exception(err);
        }

        // update title
        document.querySelector("#title #group-name").innerHTML = data.name;

        // add basic info pane
        var infoEl = document.createElement("div")

        function addRow(labelStr, el) {
            var header = document.createElement("h3");
            header.innerHTML = labelStr;
            infoEl.appendChild(header);
            infoEl.appendChild(el);
        }

        var img = document.createElement("img");
        img.src = data.image_url;
        img.height = 100;

        addRow("Picture", img)

        var createdAtDate = new Date(1000 * parseInt(data.created_at));
        var dateEl = document.createTextNode("" + createdAtDate);
        addRow("Created At", dateEl);

        var membersEl = document.createElement("ul");
        data.members.sort(function(a, b) {
            return a.nickname.localeCompare(b.nickname);
        });
        data.members.forEach(function(member) {
            var li = document.createElement("li");
            if (member.image_url !== null) {
                var img = document.createElement("img");
                img.src = member.image_url;
                img.height = 50;
                li.appendChild(img);
            }
            li.appendChild(document.createTextNode(member.nickname));
            if (member.muted) {
                li.appendChild(document.createTextNode("(muted)"));
            }
            membersEl.appendChild(li);
        });
        var memberTitleStr = "Members (" + data.members.length + ")";
        addRow(memberTitleStr, membersEl);

        var messagesEl = document.createTextNode("" + data.messages.count);
        addRow("Message Count", messagesEl);

        addAnalysis("Group Info", infoEl);

    });
}

function renderTotalVsLikes() {
    d3.json("counts.json", function(err, data) {
        data.sort(function(a, b) {
            return b.total - a.total;
        });
        if (err != null) {
            throw new Exception(err);
        }

        var color = d3.scale.category20();

        var margin = {top: 20, right: 15, bottom: 60, left: 60}
        , width = 700 - margin.left - margin.right
        , height = 500 - margin.top - margin.bottom;

        var x = d3.scale.linear()
        .domain([0, d3.max(data, function(d) { return d.total; })])
        .range([ 0, width - 200 ]);

        var y = d3.scale.linear()
        .domain([0, d3.max(data, function(d) { return d.likes; })])
        .range([ height, 0 ]);

        var outputEl = document.createElement("div");
        var tt = document.createElement("div");
        d3.select(tt)
            .classed("tooltip", true)
            .style("opacity", 0)
            .style("position", "fixed")
            .style("font-size", "12px")
        outputEl.appendChild(tt);

        var chart = d3.select(outputEl)
        .append('svg:svg')
        .attr('width', width + margin.right + margin.left)
        .attr('height', height + margin.top + margin.bottom)
        .attr('class', 'chart')

        var main = chart.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'main')

        // draw the x axis
        var xAxis = d3.svg.axis()
        .scale(x)
        .orient('bottom');

        main.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .attr('class', 'main axis date')
        .call(xAxis)
        .append("text")
        .attr("class", "label")
        .attr("x", x.range()[1])
        .attr("y", -6)
        .style("text-anchor", "end")
        .text("Total Messages");

        // draw the y axis
        var yAxis = d3.svg.axis()
        .scale(y)
        .orient('left');

        main.append('g')
        .attr('transform', 'translate(0,0)')
        .attr('class', 'main axis date')
        .call(yAxis)
        .append("text")
        .attr("class", "label")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Total Likes");

        var g = main.append("svg:g");

        var dots = g.selectAll("scatter-dots")
        .data(data)
        .enter().append("svg:circle")
        .attr("cx", function (d,i) { return x(d.total); } )
        .attr("cy", function (d) { return y(d.likes); } )
        .attr("r", 8)
        .style("fill", function(d, i) {return color(i)})
        .on("mouseover", function(d, i) {
            function dim(_, i2) {
                if (i == i2) {
                    return 1;
                } else {
                    return 0.25;
                }
            }
            var ttLeft = this.getBoundingClientRect().left - 25;
            var ttTop = this.getBoundingClientRect().top + 30;
            console.log(ttLeft, ttTop);
            dots.transition().duration(250).style("opacity", dim);
            legend.transition().duration(250).style("opacity", dim);
            d3.select(tt).transition()
            .duration(250)
            .style("opacity", 0.9);
            d3.select(tt).html("<center><b>" + d.nickname + "</b></center>" + d.total + " Messages<br>" + d.likes + " Likes")
            .style("left", ttLeft + "px")
            .style("top", ttTop + "px");

        })
        .on("mouseout", function(d) {
            dots.transition().duration(250).style("opacity", 1)
            legend.transition().duration(250).style("opacity", 1);
            d3.select(tt).transition().duration(250).style("opacity", 0);
            d3.select(tt).html("");
        })

        // draw legend
        var legend = g.selectAll(".legend")
        .data(data)
        .enter().append("g")
        .attr("class", "legend")
        .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });
        // draw legend colored rectangles
        legend.append("rect")
        .attr("x", width - 18)
        .attr("width", 18)
        .attr("height", 18)
        .style("fill", function(_, i) {return color(i); });

        // draw legend text
        legend.append("text")
        .attr("x", width - 24)
        .attr("y", 9)
        .attr("dy", ".35em")
        .style("text-anchor", "end")
        .text(function(d) { return d.nickname;})

        addAnalysis("Messages vs. Likes", outputEl);

    });

}

function renderTfidf() {
    d3.json("tfidf.json", function(err, data) {
        if (err != null) {
            throw new Exception(err);
        }
        var tfidfEl = document.createElement("div");
        addAnalysis("TF-IDF", tfidfEl);
        data.forEach(function(datum) {
            var personHeader = document.createElement("h3");
            personHeader.appendChild(document.createTextNode(datum.nickname))
            tfidfEl.appendChild(personHeader);
            var scale = d3.scale.linear()
                .domain(d3.extent(datum.terms, function(x) { return x.score; }))
                .range([12,30]);
            console.log(scale.domain());
            var ol = d3.select(tfidfEl).append("ol");
            datum.terms.forEach(function(termData) {
                var text = ol.append('li').append("span")
                    .style("font-size", scale(termData.score) + "px")
                    .text(termData.term);
            });
        });
    });
}
