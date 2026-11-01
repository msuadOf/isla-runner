#define _GNU_SOURCE
#include <z3.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned long seq=0;
static void logline(const char *stage,unsigned long id,const char *kind,void *solver,double start,int result,unsigned n){pthread_mutex_lock(&lock);FILE*f=fopen(getenv("ISLA_QUERY_LOG"),"a");if(!f)abort();fprintf(f,"%s\t%lu\t%s\t%p\t%.9f\t%.9f\t%d\t%u\n",stage,id,kind,solver,now(),now()-start,result,n);fclose(f);pthread_mutex_unlock(&lock);}
static unsigned long begin(Z3_context c,Z3_solver s,const char *kind,unsigned n,const Z3_ast *as,double start){pthread_mutex_lock(&lock);unsigned long id=++seq;pthread_mutex_unlock(&lock);logline("begin",id,kind,s,start,0,n);const char *target=getenv("ISLA_DUMP_QUERY");if(target&&strtoul(target,0,10)==id){const char *dir=getenv("ISLA_DUMP_DIR");char path[4096];snprintf(path,sizeof(path),"%s/query-%lu.smt2",dir,id);FILE*f=fopen(path,"w");if(!f)abort();fprintf(f,"; observation dump query %lu: existing assertions then assumptions\n%s\n",id,Z3_solver_to_string(c,s));for(unsigned i=0;i<n;i++)fprintf(f,"(assert %s)\n",Z3_ast_to_string(c,as[i]));fprintf(f,"(check-sat-using qffp)\n");fclose(f);}
return id;}
Z3_lbool Z3_solver_check(Z3_context c,Z3_solver s){static Z3_lbool(*fn)(Z3_context,Z3_solver);if(!fn)fn=dlsym(RTLD_NEXT,"Z3_solver_check");double t=now();unsigned long id=begin(c,s,"check",0,0,t);Z3_lbool r=fn(c,s);logline("end",id,"check",s,t,r,0);return r;}
Z3_lbool Z3_solver_check_assumptions(Z3_context c,Z3_solver s,unsigned n,Z3_ast const as[]){static Z3_lbool(*fn)(Z3_context,Z3_solver,unsigned,Z3_ast const[]);if(!fn)fn=dlsym(RTLD_NEXT,"Z3_solver_check_assumptions");double t=now();unsigned long id=begin(c,s,"assuming",n,as,t);Z3_lbool r=fn(c,s,n,as);logline("end",id,"assuming",s,t,r,n);return r;}
