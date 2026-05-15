const fs = require("fs");
const path = require("path");
const Module = require("module");

const originalResolveFilename = Module._resolveFilename;
const webpackRuntimeSuffix = path.join(".next", "server", "webpack-runtime.js");

Module._resolveFilename = function patchedResolveFilename(request, parent, ...rest) {
  try {
    return originalResolveFilename.call(this, request, parent, ...rest);
  } catch (error) {
    if (
      !error ||
      error.code !== "MODULE_NOT_FOUND" ||
      typeof request !== "string" ||
      !request.startsWith("./")
    ) {
      throw error;
    }

    const parentFilename = parent?.filename;

    if (
      typeof parentFilename !== "string" ||
      !parentFilename.endsWith(webpackRuntimeSuffix)
    ) {
      throw error;
    }

    const directPath = path.join(
      path.dirname(parentFilename),
      request.slice(2)
    );

    if (fs.existsSync(directPath)) {
      return directPath;
    }

    const redirectedPath = path.join(
      path.dirname(parentFilename),
      "chunks",
      path.basename(request)
    );

    if (fs.existsSync(redirectedPath)) {
      return redirectedPath;
    }

    throw error;
  }
};
