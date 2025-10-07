const express = require("express");
const app = express();

app.get("/", (req, res) => {
  res.send("Hello World!");
});

/* Route paths based on string patterns */

// This route path will match acd and abcd.
app.get("/ab?cd", (req, res) => {
  res.send("ab?cd");
  console.log(
    `Route accessed: ${req.path} | Pattern matched: /ab?cd | Request method: ${req.method}`
  );
});

// This route path will match abcd, abbcd, abbbcd, and so on.
app.get("/ab+cd", (req, res) => {
  res.send("ab+cd");
  console.log(`Route accessed: ${req.path} | Pattern matched: /ab+cd`);
});

// This route path will match abcd, abxcd, abRANDOMcd, ab123cd, and so on.
app.get("/ab*cd", (req, res) => {
  res.send("ab*cd");
  console.log(`Route accessed: ${req.path} | Pattern matched: /ab*cd`);
});

// This route path will match /abe and /abcde.
app.get("/ab(cd)?e", (req, res) => {
  res.send("ab(cd)?e");
  console.log(`Route accessed: ${req.path} | Pattern matched: /ab(cd)?e`);
});

/* Route paths based on regular expressions */

// This route path will match anything with an “z” in it.
app.get(/z/, (req, res) => {
  res.send("/z/");
  console.log(`Route accessed: ${req.path} | Pattern matched: /z/`);
});

// This route path will match butterfly and dragonfly,
// but not butterflyman, dragonflyman, and so on.
app.get(/.*fly$/, (req, res) => {
  res.send("/.*fly$/");
  console.log(`Route accessed: ${req.path} | Pattern matched: /.*fly$/`);
});

/* Route Parameters */

// Route: /users/user34; can match [A-Za-z0-9_]
app.get("/users/:userId", (req, res) => {
  res.send(req.params);
  console.log(`Route accessed: ${req.path} | Pattern matched: /users/:userId`);
});

// Route: /users/34; can match only digits [0-9]
app.get("/users-special/:userId(\\d+)", (req, res) => {
  res.send(req.params);
  console.log(`Route accessed: ${req.path} | Pattern matched: /users/:userId`);
});

// Route: /users/34/books/8989
app.get("/users/:userId/books/:bookId", (req, res) => {
  res.send(req.params);
  console.log(`Route accessed: ${req.path}`);
  console.log(`Pattern matched: /users/:userId/books/:bookId`);
});

// Route: /flights/LAX-SFO
app.get("/flights/:from-:to", (req, res) => {
  res.send(req.params);
});

// Route: /plantae/Prunus.persica
app.get("/plantae/:genus.:species", (req, res) => {
  res.send(req.params);
});

/* Route Handlers */

const cb0 = function (req, res, next) {
  console.log("CB0");
  next();
};

const cb1 = function (req, res, next) {
  console.log("CB1");
  next();
};

app.get(
  "/example/d",
  [cb0, cb1],
  (req, res, next) => {
    console.log("the response will be sent by the next function ...");
    next();
  },
  (req, res) => {
    res.send("Hello from D!");
  }
);

app.get(
  "/protected",
  (req, res, next) => {
    const number = Math.floor(Math.random() * 10);

    if (number % 2 == 0) {
      console.log("Number is even, you can access content");
      console.log(`Number is: ${number}`);
      next();
    } else {
      console.log("Number is odd, you can't access content");
      console.log(`Number is: ${number}`);
      res.status(401).send("Unauthorized");
    }
  },
  (req, res) => {
    res.send("Protected content");
  }
);

/* HTTP Methods */

app
  .route("/book")
  .get((req, res) => {
    res.send("Get a random book");
  })
  .post((req, res) => {
    res.send("Add a book");
  })
  .put((req, res) => {
    res.send("Update the book");
  });

module.exports = app;
