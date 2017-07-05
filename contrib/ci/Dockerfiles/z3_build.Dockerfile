ARG DOCKER_IMAGE_BASE
FROM ${DOCKER_IMAGE_BASE}


# Specify defaults. This can be changed when invoking
# `docker build`.
ARG ASAN_BUILD=0
ARG BUILD_DOCS=0
ARG CC=gcc
ARG CXX=g++
ARG DOTNET_BINDINGS=1
ARG JAVA_BINDINGS=1
ARG NO_SUPPRESS_OUTPUT=0
ARG PYTHON_BINDINGS=1
ARG PYTHON_EXECUTABLE=/usr/bin/python2.7
ARG RUN_SYSTEM_TESTS=1
ARG RUN_UNIT_TESTS=1
ARG TARGET_ARCH=x86_64
ARG TEST_INSTALL=1
ARG UBSAN_BUILD=0
ARG USE_LIBGMP=0
ARG USE_LTO=0
ARG USE_OPENMP=1
ARG Z3_SRC_DIR=/home/user/z3_src
ARG Z3_BUILD_TYPE=RelWithDebInfo
ARG Z3_CMAKE_GENERATOR=Ninja
ARG Z3_INSTALL_PREFIX=/usr
ARG Z3_STATIC_BUILD=0
# Blank default indicates use latest.
ARG Z3_SYSTEM_TEST_GIT_REVISION
ARG Z3_VERBOSE_BUILD_OUTPUT=0

ENV \
  ASAN_BUILD=${ASAN_BUILD} \
  BUILD_DOCS=${BUILD_DOCS} \
  CC=${CC} \
  CXX=${CXX} \
  DOTNET_BINDINGS=${DOTNET_BINDINGS} \
  JAVA_BINDINGS=${JAVA_BINDINGS} \
  NO_SUPPRESS_OUTPUT=${NO_SUPPRESS_OUTPUT} \
  PYTHON_BINDINGS=${PYTHON_BINDINGS} \
  PYTHON_EXECUTABLE=${PYTHON_EXECUTABLE} \
  RUN_SYSTEM_TESTS=${RUN_SYSTEM_TESTS} \
  RUN_UNIT_TESTS=${RUN_UNIT_TESTS} \
  TARGET_ARCH=${TARGET_ARCH} \
  TEST_INSTALL=${TEST_INSTALL} \
  UBSAN_BUILD=${UBSAN_BUILD} \
  USE_LIBGMP=${USE_LIBGMP} \
  USE_LTO=${USE_LTO} \
  USE_OPENMP=${USE_OPENMP} \
  Z3_SRC_DIR=${Z3_SRC_DIR} \
  Z3_BUILD_DIR=/home/user/z3_build \
  Z3_CMAKE_GENERATOR=${Z3_CMAKE_GENERATOR} \
  Z3_VERBOSE_BUILD_OUTPUT=${Z3_VERBOSE_BUILD_OUTPUT} \
  Z3_STATIC_BUILD=${Z3_STATIC_BUILD} \
  Z3_SYSTEM_TEST_DIR=/home/user/z3_system_test \
  Z3_SYSTEM_TEST_GIT_REVISION=${Z3_SYSTEM_TEST_GIT_REVISION} \
  Z3_INSTALL_PREFIX=${Z3_INSTALL_PREFIX}

# We add context across incrementally to maximal cache reuse

# Build Z3
RUN mkdir -p "${Z3_SRC_DIR}" && \
  mkdir -p "${Z3_SRC_DIR}/contrib/ci/scripts"
# Deliberately leave out `contrib`
ADD /cmake ${Z3_SRC_DIR}/cmake/
ADD /doc ${Z3_SRC_DIR}/doc/
ADD /examples ${Z3_SRC_DIR}/examples/
ADD /scripts ${Z3_SRC_DIR}/scripts/
ADD /src ${Z3_SRC_DIR}/src/
ADD *.txt *.md RELEASE_NOTES ${Z3_SRC_DIR}/

ADD \
  /contrib/ci/scripts/build_z3_cmake.sh \
  /contrib/ci/scripts/set_compiler_flags.sh \
  /contrib/ci/scripts/set_generator_args.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/build_z3_cmake.sh

# Test building docs
ADD \
  /contrib/ci/scripts/test_z3_docs.sh \
  /contrib/ci/scripts/run_quiet.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/test_z3_docs.sh

# Test examples
ADD \
  /contrib/ci/scripts/test_z3_examples_cmake.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/test_z3_examples_cmake.sh

# Run unit tests
ADD \
  /contrib/ci/scripts/test_z3_unit_tests_cmake.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/test_z3_unit_tests_cmake.sh

# Run system tests
ADD \
  /contrib/ci/scripts/test_z3_system_tests.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/test_z3_system_tests.sh

# Test install
ADD \
  /contrib/ci/scripts/test_z3_install_cmake.sh \
  ${Z3_SRC_DIR}/contrib/ci/scripts/
RUN ${Z3_SRC_DIR}/contrib/ci/scripts/test_z3_install_cmake.sh
