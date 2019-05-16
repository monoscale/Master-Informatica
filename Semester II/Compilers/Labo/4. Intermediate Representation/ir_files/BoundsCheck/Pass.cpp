#include <llvm/IR/DebugInfo.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/Instructions.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/Pass.h>
#include <llvm/Support/Debug.h>

#include <list>
#include <cassert>
#include <sstream>
#include <typeinfo>

#define DEBUG_TYPE "cheetah::boundscheck"

using namespace llvm;



namespace {
    // FunctionPass operators on a function at a time
    struct BoundsCheck : public FunctionPass {
        public:
            static char ID; // PassID
            BoundsCheck() : FunctionPass(ID) { }

            /// Entry point of the pass; this function performs the actual analysis or
            /// transformation, and is called for each function in the module.
            ///
            /// The returned boolean should be `true` if the function was modified,
            /// `false` if it wasn't.
            bool runOnFunction(Function &F) override {
                LLVMContext& context = F.getContext();
                IRBuilder<> Builder(context);

                LLVM_DEBUG({
                    dbgs() << "BoundsCheck: processing function '";
                    dbgs().write_escaped(F.getName()) << "'\n";
                });

                // Instantiate the assert function once per module
                if (Assert == nullptr || Assert->getParent() != F.getParent())
                    Assert = getAssertFunction(F.getParent());
                
                    

                
                // A getelementptr instruction is used to get the address of a subelement of an aggregate data structure (arrays, structs)
                // It performs address calculation only and does not access memory
                // getelementptr       <ty>,       <ty>* <ptrval> {, [inrange] <ty> <idx>}*
                // getelementptr [10 x i32], [10 x i32]* %foo      , i32 0, i32 %0, !dbg !10
                //      [10 x i32]           specifies we have an array of ten 32bit elements.
                //      [10 x i32]* %foo     specifies the address of this array
                //      i32 0                specifies the steps from the base pointer (0 because start of array)
                //      i32 %0               specifies the index offset which gets accessed
                // Find all GEP instructions (GetElementPointer instructions)
                // https://users.elis.ugent.be/~tbesard/compilers/llvm/doxygen/d0/d74/classllvm_1_1GetElementPtrInst.html
                // NOTE: we need to do this first, because the iterators get invalidated
                //       when modifying underlying structures
                std::list<GetElementPtrInst *> WorkList;
                for (auto &FI : F)    // Iterate function -> basic blocks
                    for (auto &BI : FI)  // Iterate basic block -> instructions
                        if (auto *GEP = dyn_cast<GetElementPtrInst>(&BI))
                            WorkList.push_back(GEP);


                // Process any GEP instructions
                bool Changed = false;
                for (auto *GEP : WorkList) {
                    // IMPLEMENTATION:

                    // get debug information such as line and column of the instruction
                    const DebugLoc& debugLocation = GEP->getDebugLoc();
                    unsigned line = debugLocation.getLine();
                    unsigned column = debugLocation.getCol();
                    
                    LLVM_DEBUG(dbgs() << "\n");
                    LLVM_DEBUG(dbgs() << "BoundsCheck\tfound a GEP: " << *GEP << "\n");
                    LLVM_DEBUG(dbgs() << "BoundsCheck\tname: " << GEP->getPointerOperand()->getName() << "\n");
                    LLVM_DEBUG(dbgs() << "BoundsCheck\ttype: " << GEP->getSourceElementType()->getTypeID() << "\n");
                    LLVM_DEBUG(dbgs() << "BoundsCheck\tnumber of indices: " << GEP->getNumIndices() << "\n");
                    LLVM_DEBUG(dbgs() << "BoundsCheck\t(line, column): (" << line << "," << column << ")\n");
                    
                    assert(GEP->getSourceElementType()->getTypeID() == Type::TypeID::ArrayTyID); // 14 is ArrayTyID                    
                    
                    uint64_t numOfElements = ((ArrayType*) GEP->getSourceElementType())->getNumElements(); // this is the upper array bound
                    LLVM_DEBUG(dbgs() << "BoundsCheck\tnumber of elements:" << numOfElements << "\n");

                    uint64_t accessIndex = 4; // the index that is used to access the array

                    
                    // Case 1 : all indices are known at compile time
                    if(GEP->hasAllConstantIndices()){
                        LLVM_DEBUG(dbgs() << "BoundsCheck\tall the indices are constant" << "\n");
                        User::const_op_iterator indices = GEP->idx_begin() + 1; // skip first index ( see explanation above about getelementptr)
                        Value* iVal = indices->get();

                        assert(iVal->getType()->getTypeID() == Type::TypeID::IntegerTyID);
                        
                        ConstantInt* integer = (ConstantInt*)iVal;
                        accessIndex = integer->getValue().getLimitedValue();
                        
                        LLVM_DEBUG(dbgs() << "BoundsCheck\taccessIndex: " << accessIndex << "\n");
                        
                        if(accessIndex >= numOfElements){
                            std::ostringstream reason;
                            reason << "Index out of bounds (line " << line << ", column " << column <<  ")\n\tIndex: " << accessIndex << "\n\tMax: " << numOfElements - 1 << "\n";
                            report_fatal_error(reason.str());
                        }
                    } else {
                        Builder.SetInsertPoint(GEP->getNextNode());
                        Constant* index = ConstantInt::getSigned(Type::getInt32Ty(context), accessIndex);
                        Constant* arraySize = ConstantInt::getSigned(Type::getInt32Ty(context), numOfElements);
                        
                        ICmpInst* compareInstruction = (ICmpInst*) Builder.CreateICmpSGE(index, arraySize);

                        BasicBlock* ifTrue = BasicBlock::Create(context, "trap", &F);
                        ifTrue->getInstList().push_back(new UnreachableInst(context));
                        BasicBlock* ifFalse = BasicBlock::Create(context, "cont", &F);
                        ifFalse->getInstList().push_back(ReturnInst::Create(context, ConstantInt::getSigned(Type::getInt32Ty(context), 0)));
                                                
                        BranchInst* branchInstruction = (BranchInst*) Builder.CreateCondBr(compareInstruction, ifTrue, ifFalse);
                        branchInstruction->getParent()->dump();
                        //Builder.Insert(branchInstruction);
                    

                        //ifTrue->dump();
                        //ifFalse->dump();
                        //Builder.CreateCondBr(trueVal, ifTrue, ifFalse);
                        
                        
                        //Builder.SetInsertPoint(GEP);
                        //accessIndex = 4;
                        //// LHS =  accessIndex
                        //// RHS = size of array
                        //// cast the number of elements to a Value pointer
                        //Constant* index = ConstantInt::getSigned(Type::getInt32Ty(context), accessIndex);
                        //Constant* arraySize = ConstantInt::getSigned(Type::getInt32Ty(context), numOfElements);
                        //Twine t;
                        //ICmpInst* compareInstruction = new ICmpInst(ICmpInst::ICMP_SGE, index, arraySize, t);
                        //compareInstruction->
                        

                    }

                }
                return Changed;
            }

        private:
            Function *Assert = nullptr;
            /// Get a function object pointing to the Sys V '__assert' function.
            ///
            /// This function displays a failed assertion, together with the source
            /// location (file name and line number). Afterwards, it abort()s the program.
            Function *getAssertFunction(Module *Mod) {
                Type *CharPtrTy = Type::getInt8PtrTy(Mod->getContext());
                Type *IntTy = Type::getInt32Ty(Mod->getContext());
                Type *VoidTy = Type::getVoidTy(Mod->getContext());

                std::vector<Type *> assert_arg_types;
                assert_arg_types.push_back(CharPtrTy); // const char *__assertion
                assert_arg_types.push_back(CharPtrTy); // const char *__file
                assert_arg_types.push_back(IntTy);     // int __line

                FunctionType *assert_type = FunctionType::get(VoidTy, assert_arg_types, true);

                Function *F = Function::Create(assert_type, Function::ExternalLinkage, "__assert", Mod);
                F->addFnAttr(Attribute::NoReturn);
                F->setCallingConv(CallingConv::C);
                return F;
            }

    };
}

char BoundsCheck::ID = 0;
static RegisterPass<BoundsCheck> X("cheetah-bc",
                                   "Cheetah Bounds Check Pass", false, false);
