/*++
Copyright (c) 2006 Microsoft Corporation

Module Name:

    smtlib_solver.cpp

Abstract:

    SMT based solver.

Author:

    Nikolaj Bjorner (nbjorner) 2006-11-3.

Revision History:

--*/

#include "parsers/smt/smtparser.h"
#include "parsers/smt/smtlib_solver.h"
#include "util/warning.h"
#include "ast/ast_pp.h"
#include "ast/ast_ll_pp.h"
#include "ast/well_sorted.h"
#include "model/model.h"
#include "model/model_v2_pp.h"
#include "solver/solver.h"
#include "tactic/portfolio/smt_strategic_solver.h"
#include "cmd_context/cmd_context.h"
#include "model/model_params.hpp"
#include "parsers/util/parser_params.hpp"

namespace smtlib {

    solver::solver():
        m_ast_manager(m_params.m_proof ? PGM_ENABLED : PGM_DISABLED, 
                      m_params.m_trace ? m_params.m_trace_file_name.c_str() : 0),
        m_ctx(0),
        m_error_code(0) {
        parser_params ps;
        m_parser = parser::create(m_ast_manager, ps.ignore_user_patterns());
        m_parser->initialize_smtlib();
    }

    solver::~solver() {
        if (m_ctx)
            dealloc(m_ctx);
    }

    bool solver::solve_smt(char const * benchmark_file) {    
        IF_VERBOSE(100, verbose_stream() << "parsing...\n";);
        if (!m_parser->parse_file(benchmark_file)) {
            if (benchmark_file) {
                warning_msg("could not parse file '%s'.", benchmark_file);
            }
            else {
                warning_msg("could not parse input stream.");
            }
            m_error_code = ERR_PARSER;
            return false;
        }
        benchmark * benchmark = m_parser->get_benchmark();
        solve_benchmark(*benchmark);
        return true;
    }

    bool solver::solve_smt_string(char const * benchmark_string) {    
        if (!m_parser->parse_string(benchmark_string)) {
            warning_msg("could not parse string '%s'.", benchmark_string);
            return false;
        }
        benchmark * benchmark = m_parser->get_benchmark();
        solve_benchmark(*benchmark);
        return true;
    }
    
    void solver::display_statistics() {
        if (m_ctx)
            m_ctx->display_statistics();
    }

    void solver::solve_benchmark(benchmark & benchmark) {
        if (benchmark.get_num_formulas() == 0) {
            // Hack: it seems SMT-LIB allow benchmarks without any :formula
            benchmark.add_formula(m_ast_manager.mk_true());
        }
        m_ctx = alloc(cmd_context, true, &m_ast_manager, benchmark.get_logic());
        m_ctx->set_solver_factory(mk_smt_strategic_solver_factory());
        theory::expr_iterator fit  = benchmark.begin_formulas();
        theory::expr_iterator fend = benchmark.end_formulas();
        for (; fit != fend; ++fit)
            solve_formula(benchmark, *fit);
    }

    void solver::solve_formula(benchmark const & benchmark, expr * f) {
        IF_VERBOSE(100, verbose_stream() << "starting...\n";);
        m_ctx->reset();
        for (unsigned i = 0; i < benchmark.get_num_axioms(); i++) 
            m_ctx->assert_expr(benchmark.get_axioms()[i]);
        m_ctx->assert_expr(f);
        m_ctx->check_sat(benchmark.get_num_assumptions(), benchmark.get_assumptions());
        check_sat_result * r = m_ctx->get_check_sat_result();
        if (r != 0) {
            proof * pr = r->get_proof();
            if (pr != 0 && m_params.m_proof)
                std::cout << mk_ll_pp(pr, m_ast_manager, false, false);
            model_ref md;
            if (r->status() != l_false) r->get_model(md);
            if (md.get() != 0 && m_params.m_model) {
                model_params p;
                model_v2_pp(std::cout, *(md.get()), p.partial());
            }
        }
        else {
            m_error_code = ERR_UNKNOWN_RESULT;
        }
    }
};
