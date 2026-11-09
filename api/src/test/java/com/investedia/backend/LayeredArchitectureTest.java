package com.investedia.backend;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;

class LayeredArchitectureTest {
    @Test
    void controllersDoNotAccessRepositoriesOrFilesDirectly() {
        var classes = new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.investedia.backend");
        noClasses().that().resideInAPackage("..controller..")
                .should().dependOnClassesThat().resideInAnyPackage("..repository..", "java.nio.file..", "java.sql..")
                .check(classes);
    }

    @Test
    void servicesAndRepositoriesKeepDependencyDirection() {
        var classes = new ClassFileImporter().withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                .importPackages("com.investedia.backend");
        noClasses().that().resideInAPackage("..service..")
                .should().dependOnClassesThat().resideInAnyPackage("..controller..", "..repository.file..", "jakarta.servlet..", "java.nio.file..")
                .check(classes);
        noClasses().that().resideInAPackage("..repository..")
                .should().dependOnClassesThat().resideInAnyPackage("..controller..", "..service..")
                .check(classes);
        slices().matching("com.investedia.backend.(*)..").should().beFreeOfCycles().check(classes);
    }
}
