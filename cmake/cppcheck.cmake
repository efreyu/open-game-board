find_program(CPPCHECK_BIN NAMES cppcheck)

if(CPPCHECK_BIN)
    message(STATUS "Found: cppcheck")
    list(
            APPEND CMAKE_CXX_CPPCHECK
            "${CPPCHECK_BIN}"
            "--enable=all"
            "--cppcheck-build-dir=${CMAKE_BINARY_DIR}"
            "--enable=warning,performance,portability,style"
            "--inconclusive"
            "--check-config"
            "--force"
            "--inline-suppr"
            "--suppressions-list=${CMAKE_SOURCE_DIR}/tools/config/cppcheck_suppressions.txt"
            "-i ${CMAKE_BINARY_DIR}/thirdparty"
            "--xml"
            "--output-file=${CMAKE_BINARY_DIR}/cppcheck.xml"
            "--checkers-report=${CMAKE_BINARY_DIR}/cppcheck_report.xml"
    )
endif()
